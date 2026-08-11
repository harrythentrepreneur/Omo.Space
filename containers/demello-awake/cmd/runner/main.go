// demello-runner is the dependency-free process boundary between Modal and the
// Python media workflow. It accepts only explicit absolute request/result paths,
// forwards termination to the whole child process group, and validates the one
// typed result document before returning success.
package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"regexp"
	"syscall"
	"time"
)

var runIDPattern = regexp.MustCompile(`^[A-Za-z0-9_-]{8,96}$`)

type artifact struct {
	Key    string `json:"key"`
	SHA256 string `json:"sha256"`
	Bytes  int64  `json:"bytes"`
}

type artifacts struct {
	Video        artifact `json:"video"`
	ContactSheet artifact `json:"contact_sheet"`
}

type framesUsed struct {
	Generated int `json:"generated"`
	Semantic  int `json:"semantic"`
	Output    int `json:"output"`
}

type media struct {
	DurationSeconds float64 `json:"duration_seconds"`
	VideoCodec      string  `json:"video_codec"`
	AudioCodec      string  `json:"audio_codec"`
	Width           int     `json:"width"`
	Height          int     `json:"height"`
	FPS             float64 `json:"fps"`
}

type usage struct {
	ProviderCostsUSD      map[string]float64 `json:"provider_costs_usd"`
	ProviderCostsComplete bool               `json:"provider_costs_complete"`
	ModalCPUCoreSeconds   float64            `json:"modal_cpu_core_seconds"`
	ModalMemoryGiBSeconds float64            `json:"modal_memory_gib_seconds"`
	ArtifactStorageUSD    float64            `json:"artifact_storage_usd"`
	ArtifactEgressUSD     float64            `json:"artifact_egress_usd"`
}

type pricingHistory struct {
	StaticEstimateUSD      float64   `json:"static_estimate_usd"`
	SuccessfulDeliveredUSD []float64 `json:"successful_delivered_usd"`
	Delivered7dUSD         float64   `json:"delivered_7d_usd"`
	Delivered30dUSD        float64   `json:"delivered_30d_usd"`
}

type resultDocument struct {
	RunID              string         `json:"run_id"`
	Status             string         `json:"status"`
	Artifacts          artifacts      `json:"artifacts"`
	FramesUsed         framesUsed     `json:"frames_used"`
	Usage              usage          `json:"usage"`
	PricingHistory     pricingHistory `json:"pricing_history"`
	Media              media          `json:"media"`
	GenerationProvider string         `json:"generation_provider"`
}

func regularAbsoluteInput(name, value string) (string, error) {
	if value == "" || !filepath.IsAbs(value) {
		return "", fmt.Errorf("%s must be an absolute path", name)
	}
	clean := filepath.Clean(value)
	info, err := os.Lstat(clean)
	if err != nil {
		return "", fmt.Errorf("%s is unavailable", name)
	}
	if info.Mode()&os.ModeSymlink != 0 || !info.Mode().IsRegular() {
		return "", fmt.Errorf("%s must be a regular non-symlink file", name)
	}
	return clean, nil
}

func validatedResultPath(value string) (string, error) {
	if value == "" || !filepath.IsAbs(value) {
		return "", errors.New("result must be an absolute path")
	}
	clean := filepath.Clean(value)
	if _, err := os.Lstat(clean); err == nil {
		return "", errors.New("result path already exists")
	} else if !os.IsNotExist(err) {
		return "", errors.New("result path cannot be inspected")
	}
	parentInfo, err := os.Stat(filepath.Dir(clean))
	if err != nil || !parentInfo.IsDir() {
		return "", errors.New("result parent must be an existing directory")
	}
	return clean, nil
}

func validateResult(path, expectedRunID string) error {
	info, err := os.Lstat(path)
	if err != nil || info.Mode()&os.ModeSymlink != 0 || !info.Mode().IsRegular() {
		return errors.New("workflow did not create a regular result file")
	}
	if info.Size() <= 0 || info.Size() > 1<<20 {
		return errors.New("workflow result size is invalid")
	}
	handle, err := os.Open(path)
	if err != nil {
		return errors.New("workflow result cannot be opened")
	}
	defer handle.Close()
	decoder := json.NewDecoder(io.LimitReader(handle, (1<<20)+1))
	decoder.DisallowUnknownFields()
	var result resultDocument
	if err := decoder.Decode(&result); err != nil {
		return errors.New("workflow result is not the typed JSON contract")
	}
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		return errors.New("workflow result contains trailing data")
	}
	if result.RunID != expectedRunID || !runIDPattern.MatchString(result.RunID) {
		return errors.New("workflow result run_id mismatch")
	}
	if result.Status != "completed" {
		return errors.New("workflow result is not completed")
	}
	prefix := "runs/" + result.RunID + "/"
	if result.Artifacts.Video.Key != prefix+"video.mp4" ||
		result.Artifacts.ContactSheet.Key != prefix+"contact-sheet.jpg" {
		return errors.New("workflow artifact keys violate the exact run path")
	}
	if result.Artifacts.Video.Bytes <= 0 || result.Artifacts.ContactSheet.Bytes <= 0 ||
		result.Artifacts.Video.SHA256 == "" || result.Artifacts.ContactSheet.SHA256 == "" {
		return errors.New("workflow artifact evidence is incomplete")
	}
	if result.FramesUsed.Generated <= 0 || result.FramesUsed.Semantic <= 0 || result.FramesUsed.Output <= 0 {
		return errors.New("workflow frame evidence is invalid")
	}
	if result.Media.DurationSeconds <= 0 || result.Media.VideoCodec != "h264" ||
		result.Media.AudioCodec != "aac" || result.Media.Width != 1080 ||
		result.Media.Height != 1920 || result.Media.FPS != 30 {
		return errors.New("workflow media contract is invalid")
	}
	if result.GenerationProvider != "openai" && result.GenerationProvider != "openai-codex-subscription" && result.GenerationProvider != "procedural-fallback" {
		return errors.New("workflow generation provider is invalid")
	}
	return nil
}

func executeChild(python, workflow, request, result string) error {
	command := exec.Command(python, workflow, "--request", request, "--result", result)
	command.Env = os.Environ()
	// Provider SDK output is not part of the protocol and may contain sensitive
	// request bodies. The runner emits only fixed, redacted failure messages.
	command.Stdout = io.Discard
	command.Stderr = io.Discard
	command.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	if err := command.Start(); err != nil {
		return errors.New("workflow process could not start")
	}

	wait := make(chan error, 1)
	go func() { wait <- command.Wait() }()
	signals := make(chan os.Signal, 2)
	signal.Notify(signals, os.Interrupt, syscall.SIGTERM, syscall.SIGQUIT)
	defer signal.Stop(signals)

	select {
	case err := <-wait:
		if err != nil {
			return errors.New("workflow process failed")
		}
		return nil
	case incoming := <-signals:
		forward, ok := incoming.(syscall.Signal)
		if !ok {
			forward = syscall.SIGTERM
		}
		_ = syscall.Kill(-command.Process.Pid, forward)
		select {
		case <-wait:
			return errors.New("workflow process cancelled")
		case <-time.After(10 * time.Second):
			_ = syscall.Kill(-command.Process.Pid, syscall.SIGKILL)
			<-wait
			return errors.New("workflow process cancelled")
		}
	}
}

func run(arguments []string) error {
	flags := flag.NewFlagSet("demello-runner", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	requestArg := flags.String("request", "", "absolute request JSON path")
	resultArg := flags.String("result", "", "absolute result JSON path")
	pythonArg := flags.String("python", "/usr/local/bin/python3", "Python executable")
	workflowArg := flags.String("workflow", "/root/demello_awake/workflow.py", "workflow entrypoint")
	if err := flags.Parse(arguments); err != nil || flags.NArg() != 0 {
		return errors.New("invalid or ambiguous invocation arguments")
	}
	request, err := regularAbsoluteInput("request", *requestArg)
	if err != nil {
		return err
	}
	result, err := validatedResultPath(*resultArg)
	if err != nil {
		return err
	}
	if request == result {
		return errors.New("request and result paths must differ")
	}
	workflow, err := regularAbsoluteInput("workflow", *workflowArg)
	if err != nil {
		return err
	}
	if *pythonArg == "" {
		return errors.New("python executable is required")
	}

	var envelope struct {
		RunID string `json:"run_id"`
	}
	handle, err := os.Open(request)
	if err != nil {
		return errors.New("request cannot be opened")
	}
	decoder := json.NewDecoder(io.LimitReader(handle, (1<<20)+1))
	err = decoder.Decode(&envelope)
	handle.Close()
	if err != nil || !runIDPattern.MatchString(envelope.RunID) {
		return errors.New("request JSON has an invalid run_id")
	}

	if err := executeChild(*pythonArg, workflow, request, result); err != nil {
		return err
	}
	return validateResult(result, envelope.RunID)
}

func main() {
	if err := run(os.Args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, "demello-runner: execution failed")
		os.Exit(1)
	}
}

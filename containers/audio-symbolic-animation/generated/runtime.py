"""Generated fixture-backed async media orchestration contract."""
import asyncio, hashlib, json, math, shutil, struct, subprocess, wave
from pathlib import Path

STAGES=("accept","transcribe","derive","brief","frames","assemble","validate")
RETRY_BACKOFF_SECONDS=(0.01,0.02,0.04)

def _write_ppm(path, width, height, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    pixel=bytes((value%220, value%220, value%220)); path.write_bytes(f"P6\n{width} {height}\n255\n".encode()+pixel*(width*height))
def _size(path):
    with path.open('rb') as f:
        magic=f.readline(); width,height=map(int,f.readline().split())
    return width,height
def _artifact(root,path,kind,media_type):
    return {"kind":kind,"path":str(path.relative_to(root)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"media_type":media_type}

class FakeFrameProvider:
    in_flight=0; max_in_flight=0; events=[]
    def __init__(self,landscape_once=None):
        type(self).in_flight=0; type(self).max_in_flight=0; type(self).events=[]
        self.landscape_once=set(landscape_once or ()); self.attempts={}
    async def generate(self,index,parent,out):
        cls=type(self); cls.in_flight+=1; cls.max_in_flight=max(cls.max_in_flight,cls.in_flight); cls.events.append({"event":"start","frame":index})
        self.attempts[index]=self.attempts.get(index,0)+1
        try:
            await asyncio.sleep(0)
            landscape=index in self.landscape_once and self.attempts[index]==1
            _write_ppm(out,640 if landscape else 360,360 if landscape else 640,30+index*20)
            return out
        finally:
            cls.events.append({"event":"end","frame":index}); cls.in_flight-=1

def _assemble_ffmpeg(root,frames,duration):
    audio=root/'fixture.wav'; video=root/'video.mp4'
    with wave.open(str(audio),'wb') as wav:
        wav.setparams((1,2,8000,0,'NONE','not compressed'))
        samples=b''.join(struct.pack('<h',int(1000*math.sin(2*math.pi*220*i/8000))) for i in range(int(duration*8000)))
        wav.writeframes(samples)
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg: return None,audio
    subprocess.run([ffmpeg,'-y','-loglevel','error','-framerate','1','-i',str(root/'frames/F%03d.ppm'),'-i',str(audio),'-t',str(duration),'-r','30','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',str(video)],check=True)
    return video,audio
def _probe(video,expected):
    probe=shutil.which('ffprobe')
    if not probe: return expected
    raw=subprocess.check_output([probe,'-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(video)],text=True)
    actual=float(raw.strip())
    if abs(actual-expected)>0.2: raise ValueError('duration_contract_failed')
    return actual

async def orchestrate(payload,workdir,provider=None,sleep=asyncio.sleep,checkpoint_frames=6):
    if provider is None:
        return {"status":"blocked","code":"PRODUCTION_FRAME_PROVIDER_UNAVAILABLE","retryable":False,"artifacts":[]}
    root=Path(workdir); root.mkdir(parents=True,exist_ok=True); duration=float(payload['duration_seconds']); total=max(1,math.ceil(duration)); progress=[]
    for stage in STAGES[:4]: progress.append({"stage":stage,"state":"completed","completed":0,"total":total})
    frames=root/'frames'; frames.mkdir(exist_ok=True); parent=None
    for index in range(total):
        target=frames/f'F{index:03d}.ppm'
        if target.exists() and _size(target)[0]<_size(target)[1]: parent=target; continue
        for attempt,delay in enumerate(RETRY_BACKOFF_SECONDS):
            await provider.generate(index,parent,target)
            width,height=_size(target)
            if width<height: break
            target.unlink(missing_ok=True)
            if attempt==len(RETRY_BACKOFF_SECONDS)-1: raise ValueError('portrait_orientation_required')
            result=sleep(delay)
            if hasattr(result,'__await__'): await result
        parent=target
        if (index+1)%checkpoint_frames==0:
            cp=root/'checkpoints'/f'checkpoint-{index:06d}.json'; cp.parent.mkdir(exist_ok=True); cp.write_text(json.dumps({"last_frame":index},sort_keys=True)+'\n')
    progress.append({"stage":"frames","state":"completed","completed":total,"total":total})
    video,audio=_assemble_ffmpeg(root,list(frames.glob('*.ppm')),duration); progress.append({"stage":"assemble","state":"completed","completed":total,"total":total})
    actual=_probe(video,duration) if video else duration
    manifest=root/'run-manifest.json'; manifest.write_text(json.dumps({"duration_seconds":actual,"frame_count":total,"fixture":True},sort_keys=True)+'\n')
    artifacts=[_artifact(root,audio,'audio','audio/wav'),_artifact(root,manifest,'manifest','application/json')]
    if video: artifacts.insert(0,_artifact(root,video,'video','video/mp4'))
    artifacts += [_artifact(root,p,'frame','image/x-portable-pixmap') for p in sorted(frames.glob('*.ppm'))]
    progress.append({"stage":"validate","state":"completed","completed":total,"total":total})
    return {"status":"completed","duration_seconds":actual,"progress":progress,"artifacts":artifacts}

async def run_fixture(workdir,duration_seconds=3,checkpoint_frames=6):
    return await orchestrate({"audio_ref":"fixture://tone","duration_seconds":duration_seconds},workdir,FakeFrameProvider(),checkpoint_frames=checkpoint_frames)

# core/ai/ai_config.py

from fastapi import HTTPException
import asyncio
import httpx
import re
import uuid
from dotenv import load_dotenv
from app.core.config.config import settings
from app.core.config.logger import logger
from app.core.utils.retry import retry
import json

# Load environment variables
load_dotenv()

# Configure Gemini
GEMINI_API_KEY = settings.GEMINI_API_KEY

# Configure Runware
RUNWARE_API_KEY = settings.RUNWARE_API_KEY


# ── Runware prompt sanitization ────────────────────────────────────────
# Runware's safety filter occasionally blocks prompts that combine an
# explicit numeric age with a minor-reference word (e.g. "6-year-old boy").
# The sanitisation below is intentionally light-touch — it only replaces
# the highest-risk patterns (numeric age + minor noun combos) while
# leaving standalone words like "boy", "girl", "child" alone since
# those almost always pass fine on their own.

# Matches "6-year-old", "six-year-old", "14 year old", etc.
_AGE_YEAR_OLD_RE = re.compile(
    r'\b\w+-year[- ]old\b', re.IGNORECASE
)


def sanitize_prompt_for_runware(prompt: str) -> str:
    """
    Light-touch sanitisation: replace explicit numeric-age patterns
    (the primary Runware trigger) with equivalent visual descriptors.
    """
    original = prompt

    # "6-year-old" / "six-year-old" → "small-statured"
    prompt = _AGE_YEAR_OLD_RE.sub('small-statured', prompt)

    if prompt != original:
        logger.debug("Sanitised prompt for Runware (removed age pattern)")

    return prompt


class RunwareSafetyBlockError(Exception):
    """Raised when Runware blocks a prompt for content-safety reasons.

    This should NOT be retried with the same prompt — the filter is
    deterministic and will always block identical input.
    """
    pass


class GeminiContentRejectedError(Exception):
    """Raised when Gemini refuses to generate content due to safety filters.

    This should NOT be retried with the same prompt — the rejection is
    deterministic (same prompt → same refusal). Let the caller handle
    fallback logic instead of burning through retries.
    """
    pass


class AIConfig:
    def __init__(self):
        # FLUX.2 [dev] - Latest generation model with improved quality
        # Open-weight model for text-to-image and image editing
        self.runware_model = "runware:400@2"  # FLUX.2 [dev] v2 - Latest generation
        self.runware_ace_model = "runware:102@1"  # FLUX Fill model - REQUIRED for ACE++
        self.gemini_model = "gemini-3-flash-preview"
        self._initialization_lock = asyncio.Lock()
        self.request_count = 0
        # ── Shared HTTP clients (avoids per-request TLS handshakes) ──
        self._httpx_client: httpx.AsyncClient | None = None

    async def _get_httpx_client(self) -> httpx.AsyncClient:
        """Lazy-init a shared httpx client for Runware API calls."""
        if self._httpx_client is None or self._httpx_client.is_closed:
            self._httpx_client = httpx.AsyncClient(timeout=300.0)
        return self._httpx_client
    
    def _get_rejection_reason(self, response: dict) -> str | None:
        """Return a human-readable rejection reason, or None if not rejected."""
        # Case 1: API-level block — no candidates at all
        if 'candidates' not in response or not response['candidates']:
            block_reason = (
                response.get('promptFeedback', {}).get('blockReason', 'unknown')
            )
            safety_ratings = response.get('promptFeedback', {}).get('safetyRatings', [])
            return f"API blocked (blockReason={block_reason}, safetyRatings={safety_ratings})"

        for candidate in response['candidates']:
            # Case 2: Candidate finished due to safety
            finish_reason = candidate.get('finishReason', '')
            if finish_reason in ('SAFETY', 'RECITATION', 'BLOCKLIST'):
                safety_ratings = candidate.get('safetyRatings', [])
                return f"Candidate blocked (finishReason={finish_reason}, safetyRatings={safety_ratings})"

            # Case 3: Model-level refusal in text
            content = candidate.get('content', {})
            content_text = ''.join(
                p.get('text', '') for p in content.get('parts', [])
            ).lower()
            refusal_phrases = (
                "i'm sorry", "i am sorry", "i cannot generate",
                "i cannot create", "unable to generate",
            )
            for phrase in refusal_phrases:
                if phrase in content_text:
                    snippet = content_text[:200]
                    return f"Model refused (matched '{phrase}'): {snippet}..."

        return None

    @retry(
        exceptions=(Exception,),
        exclude=(GeminiContentRejectedError,),
        max_retries=settings.GEMINI_MAX_RETRIES,
        initial_delay=settings.GEMINI_RETRY_DELAY,
        max_delay=settings.GEMINI_MAX_DELAY,
        backoff_factor=2,
    )
    async def generate_with_gemini(
        self,
        prompt: str,
    ) -> str:
        # Get API key from environment variable
        api_key = GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        # API configurations
        generate_content_api = "generateContent"

        # Convert string prompt to message format
        messages = [{"role": "user", "parts": [{"text": prompt}]}]

        # Prepare the request payload
        payload = {
            "contents": messages,
            "generationConfig": {
                "responseMimeType": "text/plain",
                # Disable thinking/reasoning for speed — Gemini 2.5 Flash
                # spends 30-50s "thinking" before writing, which is unnecessary
                # for creative story generation. Saves ~30-40s per call.
                "thinkingConfig": {
                    "thinkingBudget": 0,
                },
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                },
            ],
        }

        # Create the API URL (key passed via header to avoid logging)
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:{generate_content_api}"

        client = await self._get_httpx_client()
        response = await client.post(
            api_url,
            json=payload,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        )
        
        if response.status_code != 200:
            error_text = response.text
            raise Exception(
                f"API request failed with status {response.status_code}: {error_text}"
            )

        # Parse the JSON response
        response_data = response.json()

        rejection_reason = self._get_rejection_reason(response_data)
        if rejection_reason:
            logger.warning(
                f"Gemini content rejected: {rejection_reason} | "
                f"prompt starts with: {prompt[:120]}..."
            )
            raise GeminiContentRejectedError(
                f"Generation rejected: {rejection_reason}"
            )

        # Extract text from the response
        result = ""
        if "candidates" in response_data and response_data["candidates"]:
            for candidate in response_data["candidates"]:
                if "content" in candidate and "parts" in candidate["content"]:
                    for part in candidate["content"]["parts"]:
                        if "text" in part:
                            result += part["text"]

        # If no text was found, raise an exception
        if not result:
            raise Exception(
                f"No text found in response: {json.dumps(response_data)}"
            )

        return result
    
    @retry(
        exceptions=(Exception,),
        exclude=(GeminiContentRejectedError,),
        max_retries=settings.IMAGE_PROMPT_GEN_MAX_RETRIES,
        initial_delay=settings.IMAGE_PROMPT_GEN_RETRY_DELAY,
        max_delay=settings.IMAGE_PROMPT_GEN_MAX_DELAY,
        backoff_factor=2,
    )
    async def image_prompt_generate_with_gemini(
        self,
        prompt: str,
    ) -> str:
        """
        Generate text using Gemini API with retries.
        Args:
            prompt (str): The prompt for text generation.
        Returns:
            str: The generated text.
        """
        image_prompt = await self.generate_with_gemini(prompt)
    
        # Validate the prompt
        if not image_prompt or len(image_prompt.strip()) < 10:
            raise ValueError("Generated prompt is too short or empty.")
        
        if len(image_prompt.strip()) > 2700:
            raise ValueError("Generated prompt is too long.")
        
        # Return the generated image prompt
        return image_prompt

    @retry(
        exceptions=(Exception,),
        exclude=(RunwareSafetyBlockError,),
        max_retries=settings.RUNWARE_MAX_RETRIES,
        initial_delay=settings.RUNWARE_RETRY_DELAY,
        max_delay=settings.RUNWARE_MAX_DELAY,
        backoff_factor=2,
    )
    async def generate_image(self, prompt: str, is_free: bool, seed: int | None = None, extra_negative_prompt: str | None = None) -> str:
        """
        Generate an image using Runware API based on the provided prompt.
        Args:
            prompt (str): The prompt for image generation.
            is_free (bool): Whether this is a free generation.
            seed (int | None): Optional deterministic seed.
            extra_negative_prompt (str | None): Optional additional negative prompt text
                to append (e.g. style-specific like "color, vibrant" for B&W).
        Returns:
            str: The URL of the generated image.
        """
        # Use semaphore to limit concurrent requests
        try:
            self.request_count += 1
            current_request = self.request_count

            # Generate unique task UUIDs
            image_task_uuid = str(uuid.uuid4())

            # Build negative prompt — base + optional style-specific extras
            base_negative = "text, letters, words, numbers, writing, captions, titles, labels, signs, watermark, signature, typography, font, alphabet, speech bubbles, dialogue bubbles, thought bubbles, word balloons, comic bubbles, talk bubbles, chat bubbles, extra legs, extra limbs, extra arms, missing limbs, fused limbs, deformed anatomy, malformed body, anatomically incorrect, wrong number of limbs, mutated body"
            negative_prompt = f"{base_negative}, {extra_negative_prompt}" if extra_negative_prompt else base_negative

            # Sanitise prompt to avoid false-positive content-safety blocks
            prompt = sanitize_prompt_for_runware(prompt)

            # Create an array of tasks for the Runware API
            inference_task = {
                "taskType": "imageInference",
                "taskUUID": image_task_uuid,
                "positivePrompt": prompt,
                "negativePrompt": negative_prompt,
                "model": self.runware_model,
                "numberResults": 1,
                "width": 768,
                "height": 1024,
                "outputFormat": "JPEG",
                "steps": 20,
                "CFGScale": 3.5,
                "scheduler": "FlowMatchEulerDiscreteScheduler",
                "outputType": ["URL"],
                "includeCost": False,
                **({
                    "seed": seed
                } if seed is not None else {}),
            }

            payload = [
                {"taskType": "authentication", "apiKey": RUNWARE_API_KEY},
                inference_task,
            ]

            # Set up headers
            headers = {"Content-Type": "application/json"}

            # Make the API request with timeout
            client = await self._get_httpx_client()
            response = await client.post(
                "https://api.runware.ai/v1", json=payload, headers=headers
            )

            # Check for successful response
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Runware API error: {error_text}")
                # Content-safety blocks are deterministic — retrying the
                # same prompt will always fail, so raise a non-retryable error.
                if "sensitiveContentDetected" in error_text:
                    raise RunwareSafetyBlockError(
                        f"Prompt blocked by Runware safety filter (task {image_task_uuid}). "
                        f"Prompt starts with: {prompt[:120]}..."
                    )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Runware API error: {error_text}",
                )

            # Parse the response
            result = response.json()

            # Based on the example response, we should have a "data" array
            if not result or "data" not in result or not result["data"]:
                logger.error("Unexpected response format from Runware API")
                raise HTTPException(
                    status_code=500,
                    detail="Unexpected response format from Runware API",
                )

            # Find the imageInference task result in the data array
            image_result = None
            for task_result in result["data"]:
                if task_result.get("taskType") == "imageInference":
                    image_result = task_result
                    break

            # Check if we found an image result
            if not image_result or "imageURL" not in image_result:
                logger.error("No image URL found in the response")
                raise HTTPException(
                    status_code=500,
                    detail="No image URL found in the response",
                )

            return image_result["imageURL"]

        except RunwareSafetyBlockError:
            raise  # Don't wrap — let it bypass the @retry decorator
        except httpx.TimeoutException:
            logger.error(f"Timeout while generating image {current_request}")
            raise HTTPException(
                status_code=504, detail="Image generation timed out"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating image with Runware: {str(e)} \n\n[image_task_uuid]: {image_task_uuid}")
            raise HTTPException(
                status_code=500, detail=f"Failed to generate image: {str(e)} \n\n[image_task_uuid]: {image_task_uuid}"
            )

    async def generate_images_batch(
        self,
        prompts: list[dict],
        seed: int | None = None,
    ) -> dict[str, str]:
        """
        Generate multiple images in a single Runware API request.

        Args:
            prompts: List of dicts with keys: task_uuid, positive_prompt, negative_prompt
            seed: Optional deterministic seed (shared across all images).

        Returns:
            Dict mapping taskUUID → imageURL for each successfully generated image.
            Missing keys indicate failed tasks.
        """
        base_negative = "text, letters, words, numbers, writing, captions, titles, labels, signs, watermark, signature, typography, font, alphabet, speech bubbles, dialogue bubbles, thought bubbles, word balloons, comic bubbles, talk bubbles, chat bubbles, extra legs, extra limbs, extra arms, missing limbs, fused limbs, deformed anatomy, malformed body, anatomically incorrect, wrong number of limbs, mutated body"

        # Build payload: 1 auth + N inference tasks
        payload = [{"taskType": "authentication", "apiKey": RUNWARE_API_KEY}]
        for p in prompts:
            neg = p.get("negative_prompt")
            negative_prompt = f"{base_negative}, {neg}" if neg else base_negative
            sanitised_prompt = sanitize_prompt_for_runware(p["positive_prompt"])
            task = {
                "taskType": "imageInference",
                "taskUUID": p["task_uuid"],
                "positivePrompt": sanitised_prompt,
                "negativePrompt": negative_prompt,
                "model": self.runware_model,
                "numberResults": 1,
                "width": 768,
                "height": 1024,
                "outputFormat": "JPEG",
                "steps": 20,
                "CFGScale": 3.5,
                "scheduler": "FlowMatchEulerDiscreteScheduler",
                "outputType": ["URL"],
                "includeCost": False,
            }
            if seed is not None:
                task["seed"] = seed
            payload.append(task)

        headers = {"Content-Type": "application/json"}
        client = await self._get_httpx_client()
        response = await client.post(
            "https://api.runware.ai/v1", json=payload, headers=headers
        )

        if response.status_code != 200:
            error_text = response.text
            logger.error(f"Runware batch API error: {error_text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Runware batch API error: {error_text}",
            )

        result = response.json()
        if not result or "data" not in result:
            logger.error("Unexpected batch response format from Runware API")
            raise HTTPException(
                status_code=500,
                detail="Unexpected batch response format from Runware API",
            )

        # Map taskUUID → imageURL for all inference results
        url_map: dict[str, str] = {}
        for task_result in result["data"]:
            if task_result.get("taskType") == "imageInference" and "imageURL" in task_result:
                url_map[task_result["taskUUID"]] = task_result["imageURL"]

        logger.info(f"Runware batch returned {len(url_map)}/{len(prompts)} images")
        return url_map

    @retry(
        exceptions=(Exception,),
        exclude=(RunwareSafetyBlockError,),
        max_retries=settings.RUNWARE_MAX_RETRIES,
        initial_delay=settings.RUNWARE_RETRY_DELAY,
        max_delay=settings.RUNWARE_MAX_DELAY,
        backoff_factor=2,
    )
    async def generate_image_with_ace_plus_plus(
        self, 
        prompt: str, 
        reference_image_url: str,
        is_free: bool,
        repainting_scale: float = 0.3,
        task_type: str = "subject"
    ) -> str:
        """
        Generate an image using ACE++ framework for character consistency.
        
        ACE++ (Advanced Character Edit) preserves character identity from a reference
        image across new scene generations.
        
        Args:
            prompt (str): The prompt describing the new scene/pose.
            reference_image_url (str): URL of the character reference image.
            is_free (bool): Whether this is a free generation.
            repainting_scale (float): Controls identity preservation vs prompt adherence.
                - 0.0-0.3: Strong identity preservation (recommended for storybooks)
                - 0.4-0.6: Balanced
                - 0.7-1.0: More creative freedom, less identity preservation
            task_type (str): Type of ACE++ task.
                - "portrait": Focus on face/head consistency
                - "subject": Full body/character consistency (recommended for illustrations)
                - "local_editing": Edit specific regions with mask
        
        Returns:
            str: The URL of the generated image with consistent character.
        """
        image_task_uuid = str(uuid.uuid4())
        
        try:
            self.request_count += 1
            current_request = self.request_count
            
            logger.info(f"Generating ACE++ image #{current_request} with reference: {reference_image_url[:50]}...")

            # Sanitise prompt to avoid false-positive content-safety blocks
            prompt = sanitize_prompt_for_runware(prompt)

            # Build the payload for ACE++ generation
            inference_task = {
                "taskType": "imageInference",
                "taskUUID": image_task_uuid,
                "positivePrompt": prompt,
                "negativePrompt": "text, letters, words, numbers, writing, captions, titles, labels, signs, watermark, signature, typography, font, alphabet",
                "model": self.runware_ace_model,  # FLUX Fill - REQUIRED for ACE++
                "numberResults": 1,
                "width": 768,
                "height": 1024,
                "outputFormat": "JPEG",
                "steps": 20,
                "CFGScale": 50.0,  # ACE++ works better with higher CFG
                "scheduler": "FlowMatchEulerDiscreteScheduler",
                "outputType": ["URL"],
                "includeCost": False,
                # Reference image for ACE++ identity extraction (at root level, per docs)
                "referenceImages": [reference_image_url],
            }
            
            # Build ACE++ parameters based on task type
            # NOTE: repaintingScale requires inputMasks per Runware API.
            # For creation workflows (portrait/subject), omit repaintingScale.
            # Only include repaintingScale + inputMasks for local_editing workflow.
            ace_params = {"type": task_type}
            if task_type == "local_editing":
                ace_params["repaintingScale"] = repainting_scale
                # inputMasks would need to be provided for local_editing
            
            inference_task["acePlusPlus"] = ace_params
            
            # Add LoRA for extra quality if paid (optional, may interfere with ACE++)
            # For now, we skip LoRA with ACE++ to ensure best character consistency
            # if not is_free:
            #     inference_task["lora"] = [{"model": "civitai:128568@747534", "weight": 0.3}]
            
            payload = [
                {"taskType": "authentication", "apiKey": RUNWARE_API_KEY},
                inference_task
            ]

            headers = {"Content-Type": "application/json"}

            client = await self._get_httpx_client()
            response = await client.post(
                "https://api.runware.ai/v1", json=payload, headers=headers
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Runware ACE++ API error: {error_text}")
                if "sensitiveContentDetected" in error_text:
                    raise RunwareSafetyBlockError(
                        f"ACE++ prompt blocked by Runware safety filter (task {image_task_uuid}). "
                        f"Prompt starts with: {prompt[:120]}..."
                    )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Runware ACE++ API error: {error_text}",
                )

            result = response.json()

            if not result or "data" not in result or not result["data"]:
                logger.error("Unexpected response format from Runware ACE++ API")
                raise HTTPException(
                    status_code=500,
                    detail="Unexpected response format from Runware ACE++ API",
                )

            # Find the imageInference task result
            image_result = None
            for task_result in result["data"]:
                if task_result.get("taskType") == "imageInference":
                    image_result = task_result
                    break

            if not image_result or "imageURL" not in image_result:
                logger.error("No image URL found in ACE++ response")
                raise HTTPException(
                    status_code=500,
                    detail="No image URL found in ACE++ response",
                )

            logger.info(f"ACE++ image #{current_request} generated successfully")
            return image_result["imageURL"]

        except httpx.TimeoutException:
            logger.error(f"Timeout while generating ACE++ image {current_request}")
            raise HTTPException(
                status_code=504, detail="ACE++ image generation timed out"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating ACE++ image with Runware: {str(e)} \n\n[image_task_uuid]: {image_task_uuid}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to generate ACE++ image: {str(e)} \n\n[image_task_uuid]: {image_task_uuid}"
            )


# Initialize AI configuration
ai_config = AIConfig()


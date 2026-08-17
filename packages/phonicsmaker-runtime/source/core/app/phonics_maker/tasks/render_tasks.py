import asyncio
import os
import time
from pathlib import Path
from typing import Dict

from app.core.config.logger import logger
from app.core.storage.file_storage import upload_result
from app.db.models.image import SceneImage
from app.db.models.pdf import PDFGenerationResponse
from app.phonics_maker.pdf_generation import generate_story_pdf, get_task_temp_dir, cleanup_task_temp_dir, generate_default_layout_json
from app.core.error_handling.error_service import error_service
from app.core.callbacks.callback_service import callback_service
from app.core.config.config import settings
from app.phonics_maker.image_generation.image_service import ImageService, rewrite_prompt_with_change, _CHANGE_MARKER

image_service_instance = ImageService()

async def render_draft_task(task_id: str, payload: dict):
    """
    Takes a finalized draft (JSON with scenes, images, and config) and 
    bakes it directly into a PDF, bypassing the AI generation steps.
    """
    logger.info(f"Starting PDF render task for {task_id}")
    
    # 1. Extract data from payload
    story_title = payload.get("story_title", "")
    short_scenes = payload.get("scenes", [])
    raw_images = payload.get("images", [])
    phonemes = payload.get("phonemes", [])
    difficulty_level = payload.get("difficulty_level", "emergent")
    
    # Render config
    is_free = payload.get("is_free", False)
    include_activities = payload.get("include_activities", False)
    book_layout = payload.get("book_layout", "default")
    book_font = payload.get("book_font", "comic_sans")
    illustration_style = payload.get("illustration_style")
    user_email = payload.get("user_email")
    series_info = payload.get("series_info")
    focus_phonemes = payload.get("focus_phonemes")
    highlight_text = payload.get("highlight_text")
    morphology_focus = payload.get("morphology_focus")
    pre_rendered_activities_html = payload.get("pre_rendered_activities_html")
    activities = payload.get("activities")
    answer_key = payload.get("answer_key")

    # 2. Re-construct SceneImage objects
    all_images = []
    for img_dict in raw_images:
        all_images.append(SceneImage(**img_dict))
        
    base_temp_dir = Path("temp")
    base_temp_dir.mkdir(exist_ok=True)
    task_pdf_temp_dir = get_task_temp_dir(base_temp_dir, task_id)
    
    # 3. Handle Partial Redraws (Selective Image Regeneration)
    regenerate_indices = payload.get("regenerate_image_indices", [])
    
    try:
        if regenerate_indices:
            await callback_service.send_progress(task_id, 80, f"Redrawing {len(regenerate_indices)} images...")
            logger.info(f"Redrawing images for indices {regenerate_indices}")
            
            # Identify the extra negative prompt for the selected style
            extra_neg = image_service_instance.get_style_negative_prompt(illustration_style)
            
            # Regenerate requested images concurrently
            async def redraw_image(idx: int):
                # Ensure index is within bounds
                if idx < 0 or idx >= len(all_images):
                    return None

                target = all_images[idx]
                scene_id = target.scene_id

                # Fresh instance per redraw to avoid seed race conditions across concurrent redraws
                svc = ImageService()
                prompt = target.prompt
                if _CHANGE_MARKER in prompt:
                    # Prompt-edit redraw (Case B): restore original seed so layout/characters stay consistent
                    svc._book_seed = target.seed
                    parts = prompt.split(_CHANGE_MARKER, 1)
                    prompt = await rewrite_prompt_with_change(parts[0].strip(), parts[1].strip())
                # Pure regeneration (Case A): svc._book_seed stays None → random seed

                logger.info(f"Redrawing image for {scene_id}...")
                new_scene_img = await svc._generate_single_image_with_seed(
                    scene_id=scene_id,
                    prompt=prompt,
                    is_free=is_free,
                    extra_negative_prompt=extra_neg
                )
                return idx, new_scene_img

            redraw_tasks = [redraw_image(idx) for idx in regenerate_indices]
            redraw_results = await asyncio.gather(*redraw_tasks, return_exceptions=True)
            
            # Inject new images back into the pool
            for res in redraw_results:
                if isinstance(res, Exception):
                    logger.error(f"Failed to redraw an image: {res}")
                elif res is not None:
                    idx, new_scene_img = res
                    all_images[idx] = new_scene_img
                    
        await callback_service.send_progress(task_id, 85, "Baking finalized PDF")
        
        pdf_kwargs = dict(
            is_free=is_free,
            include_activities=include_activities,
            book_layout=book_layout,
            book_font=book_font,
            illustration_style=illustration_style,
            series_info=series_info,
            focus_phonemes=focus_phonemes,
            highlight_text=highlight_text,
            morphology_focus=morphology_focus,
            pre_rendered_activities_html=pre_rendered_activities_html,
        )
        
        # 3. Generate PDF
        pdf_generation_response = await generate_story_pdf(
            story_id=task_id,
            story_title=story_title,
            scenes=short_scenes,
            images=all_images,
            phonemes=phonemes,
            difficulty_level=difficulty_level,
            pre_generated_activities=(activities, answer_key) if activities and answer_key else None,
            **pdf_kwargs
        )
        
        # 4. Upload
        await callback_service.send_progress(task_id, 90, "Uploading final files")
        
        pdf_local_path = pdf_generation_response.pdf_url
        pdf_compressed_local_path = pdf_generation_response.pdf_compressed_url
        thumbnail_local_path = pdf_generation_response.thumbnail_local_path
        worksheets_local_path = pdf_generation_response.worksheets_pdf_url
        book_only_local_path = pdf_generation_response.book_only_pdf_url
        homework_local_path = pdf_generation_response.homework_pdf_url
        answer_key_local_path = pdf_generation_response.answer_key_pdf_url
        pptx_local_path = pdf_generation_response.pptx_url
        
        if settings.LOCAL_MODE:
            import shutil
            import json
            output_dir = Path(__file__).resolve().parent.parent.parent.parent / "static" / "output" / task_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Load local layout
            existing_layout = None
            local_layout_path = output_dir / f"pdf_data_{task_id}.json"
            if local_layout_path.exists():
                try:
                    with open(local_layout_path, "r") as f:
                        existing_layout = json.load(f)
                except Exception as e:
                    logger.info(f"Could not load local layout for task {task_id}: {e}")
            
            # Update/Generate
            if existing_layout:
                for idx, img_obj in enumerate(all_images):
                    if idx < len(existing_layout.get("pages", [])):
                        img_url = img_obj.image_url if hasattr(img_obj, 'image_url') else img_obj.get('image_url', '')
                        img_prompt = img_obj.prompt if hasattr(img_obj, 'prompt') else img_obj.get('prompt', '')
                        existing_layout["pages"][idx]["image_url"] = img_url
                        existing_layout["pages"][idx]["image_prompt"] = img_prompt
                layout_data = existing_layout
            else:
                layout_data = generate_default_layout_json(
                    task_id=task_id,
                    story_title=story_title,
                    scenes=short_scenes,
                    images=all_images,
                    difficulty_level=difficulty_level,
                    focus_phonemes=focus_phonemes
                )
            
            layout_temp_path = Path(pdf_local_path).parent / f"pdf_data_{task_id}.json"
            with open(layout_temp_path, "w") as f:
                json.dump(layout_data, f)

            def _local_url(path):
                if not path or not os.path.exists(path): return None
                dest = output_dir / Path(path).name
                shutil.copy2(path, dest)
                return f"http://localhost:8000/output/{task_id}/{Path(path).name}"
                
            uploaded_pdf_url = _local_url(pdf_local_path)
            uploaded_pdf_compressed_url = _local_url(pdf_compressed_local_path)
            uploaded_thumbnail_url = _local_url(thumbnail_local_path)
            uploaded_worksheets_url = _local_url(worksheets_local_path)
            uploaded_book_only_url = _local_url(book_only_local_path)
            uploaded_homework_url = _local_url(homework_local_path)
            uploaded_answer_key_url = _local_url(answer_key_local_path)
            uploaded_pptx_url = _local_url(pptx_local_path)
            _local_url(layout_temp_path)
        else:
            import urllib.request
            import json

            # Load remote layout from CDN/Spaces
            existing_layout = None
            layout_url = f"https://{settings.SPACES_NAME}.{settings.SPACES_CDN_ENDPOINT or settings.SPACES_ENDPOINT}/generated_pdfs/{task_id}/pdf_data_{task_id}.json"
            try:
                req = urllib.request.Request(
                    layout_url, 
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    existing_layout = json.loads(response.read().decode('utf-8'))
            except Exception as e:
                logger.info(f"Could not load remote layout for task {task_id}: {e}")
                
            # Update/Generate
            if existing_layout:
                for idx, img_obj in enumerate(all_images):
                    if idx < len(existing_layout.get("pages", [])):
                        img_url = img_obj.image_url if hasattr(img_obj, 'image_url') else img_obj.get('image_url', '')
                        img_prompt = img_obj.prompt if hasattr(img_obj, 'prompt') else img_obj.get('prompt', '')
                        existing_layout["pages"][idx]["image_url"] = img_url
                        existing_layout["pages"][idx]["image_prompt"] = img_prompt
                layout_data = existing_layout
            else:
                layout_data = generate_default_layout_json(
                    task_id=task_id,
                    story_title=story_title,
                    scenes=short_scenes,
                    images=all_images,
                    difficulty_level=difficulty_level,
                    focus_phonemes=focus_phonemes
                )
            
            layout_temp_path = Path(pdf_local_path).parent / f"pdf_data_{task_id}.json"
            with open(layout_temp_path, "w") as f:
                json.dump(layout_data, f)

            async def _safe_upload(path):
                if not path or not os.path.exists(path): return None, path
                try:
                    url = await upload_result(path, task_id)
                    return url, path
                except Exception as e:
                    logger.error(f"Failed to upload {path}: {e}")
                    return None, path

            upload_tasks = [
                _safe_upload(pdf_local_path),
                _safe_upload(thumbnail_local_path),
                _safe_upload(worksheets_local_path),
                _safe_upload(book_only_local_path),
                _safe_upload(homework_local_path),
                _safe_upload(answer_key_local_path),
                _safe_upload(pptx_local_path),
                _safe_upload(pdf_compressed_local_path),
                _safe_upload(str(layout_temp_path)),
            ]
            upload_results = await asyncio.gather(*upload_tasks)
            uploaded_pdf_url = upload_results[0][0]
            uploaded_thumbnail_url = upload_results[1][0]
            uploaded_worksheets_url = upload_results[2][0]
            uploaded_book_only_url = upload_results[3][0]
            uploaded_homework_url = upload_results[4][0]
            uploaded_answer_key_url = upload_results[5][0]
            uploaded_pptx_url = upload_results[6][0]
            uploaded_pdf_compressed_url = upload_results[7][0]

            # Clean up local files after all uploads complete
            for url, local_path in upload_results:
                if local_path and os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except OSError:
                        pass

        # Update images inside payload and strip keys for task control
        payload["images"] = [img.model_dump() for img in all_images]
        draft_data = {k: v for k, v in payload.items() if k not in ["task_id", "regenerate_image_indices"]}

        # 5. Send Completion Callback
        await callback_service.send_completion(
            task_id=task_id,
            pdf_url=uploaded_pdf_url,
            thumbnail_url=uploaded_thumbnail_url,
            worksheets_url=uploaded_worksheets_url,
            book_only_url=uploaded_book_only_url,
            homework_url=uploaded_homework_url,
            answer_key_url=uploaded_answer_key_url,
            pptx_url=uploaded_pptx_url,
            pdf_compressed_url=uploaded_pdf_compressed_url,
            draft_data=draft_data,
        )
        
        logger.info(f"Render task {task_id} completed successfully.")
        
    except Exception as e:
        error_service.log_error(e, context=f"Render task {task_id} failed")
        await callback_service.send_error(task_id, str(e))
        raise
    finally:
        if task_pdf_temp_dir and task_pdf_temp_dir.exists():
            cleanup_task_temp_dir(task_pdf_temp_dir)

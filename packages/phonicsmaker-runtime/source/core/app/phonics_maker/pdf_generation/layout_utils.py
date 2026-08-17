# app/phonics_maker/pdf_generation/layout_utils.py

from app.db.models.story import DifficultyLevel

def map_difficulty_to_stage(level) -> str:
    level_str = level.value if hasattr(level, 'value') else str(level)
    mapping = {
        "1": "Stage 1",
        "2": "Stage 2",
        "3": "Stage 3",
        "4": "Stage 4",
        "5": "Stage 5",
        "FOUNDATION": "Stage 1",
        "Level 1": "Stage 1",
        "Level 2": "Stage 2",
        "Level 3": "Stage 3",
        "Level 4": "Stage 4",
        "Level 5": "Stage 5",
    }
    return mapping.get(level_str, "Stage 1")

def generate_default_layout_json(task_id: str, story_title: str, scenes: list, images: list, difficulty_level, focus_phonemes: str) -> dict:
    stage_text = map_difficulty_to_stage(difficulty_level)
    phonics_text = f"Focus Sounds: {focus_phonemes}" if focus_phonemes else ""
    
    pages = []
    
    # 1. Cover Page
    cover_image_url = ""
    cover_prompt = ""
    if images:
        img_obj = images[0]
        cover_image_url = img_obj.image_url if hasattr(img_obj, 'image_url') else img_obj.get('image_url', '')
        cover_prompt = img_obj.prompt if hasattr(img_obj, 'prompt') else img_obj.get('prompt', '')
        
    cover_objects = [
        {
            "type": "text",
            "id": "font_config",
            "x": 0,
            "y": 0,
            "width": 0,
            "height": 0,
            "draggable": False,
            "fontFamily": "Comic Neue"
        },
        {
            "type": "text",
            "id": "header_level",
            "text": stage_text,
            "x": 42,
            "y": 20,
            "width": 100,
            "height": 30,
            "draggable": False,
            "fill": "#ffffff",
            "fontSize": 16
        },
        {
            "type": "text",
            "id": "header_phonics",
            "text": phonics_text,
            "x": 500,
            "y": 20,
            "width": 226,
            "height": 30,
            "draggable": False,
            "fill": "#ffffff",
            "fontSize": 16
        },
        {
            "type": "text",
            "id": "title",
            "text": story_title,
            "x": 50,
            "y": 100,
            "width": 668,
            "height": 150,
            "draggable": True,
            "fontSize": 48,
            "fontFamily": "Comic Neue",
            "fill": "#000000",
            "align": "center"
        },
        {
            "type": "text",
            "id": "subtitle",
            "text": phonics_text,
            "x": 50,
            "y": 800,
            "width": 668,
            "height": 80,
            "draggable": True,
            "fontSize": 24,
            "fontFamily": "Comic Neue",
            "fill": "#000000",
            "align": "center"
        }
    ]
    
    pages.append({
        "pageNumber": 0,
        "image_url": cover_image_url,
        "image_prompt": cover_prompt,
        "objects": cover_objects
    })
    
    # 2. Scene Pages
    for i, scene_text in enumerate(scenes):
        page_num = i + 1
        img_url = ""
        img_prompt = ""
        if page_num < len(images):
            img_obj = images[page_num]
            img_url = img_obj.image_url if hasattr(img_obj, 'image_url') else img_obj.get('image_url', '')
            img_prompt = img_obj.prompt if hasattr(img_obj, 'prompt') else img_obj.get('prompt', '')
            
        scene_objects = [
            {
                "type": "text",
                "id": f"text-{page_num}",
                "text": scene_text,
                "x": 50,
                "y": 800,
                "width": 668,
                "height": 120,
                "draggable": True,
                "fontSize": 28,
                "fontFamily": "Comic Neue",
                "fill": "#000000",
                "align": "center"
            }
        ]
        
        pages.append({
            "pageNumber": page_num,
            "image_url": img_url,
            "image_prompt": img_prompt,
            "objects": scene_objects
        })
        
    return {
        "task_id": task_id,
        "story_title": story_title,
        "pages": pages,
        "highlightEnabled": True,
        "highlightColor": "#FFF3A3"
    }

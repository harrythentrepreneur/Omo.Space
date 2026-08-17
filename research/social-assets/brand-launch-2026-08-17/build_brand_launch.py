#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import shutil, math

ROOT = Path('/root/marketplace/research/social-assets/brand-launch-2026-08-17')
POSTS = ROOT / 'posts'
SOURCES = [
    Path('/root/.hermes/cache/images/openai_codex_gpt-image-2-high_20260817_062309_f48cb4fc.png'),
    Path('/root/.hermes/cache/images/openai_codex_gpt-image-2-high_20260817_062313_d9b1c55f.png'),
    Path('/root/.hermes/cache/images/openai_codex_gpt-image-2-high_20260817_062313_f3ad21c7.png'),
    Path('/root/.hermes/cache/images/openai_codex_gpt-image-2-high_20260817_062321_06c561f6.png'),
    Path('/root/.hermes/cache/images/openai_codex_gpt-image-2-high_20260817_062352_90959a9d.png'),
]

CREAM = '#F8F7F5'
CREAM_W = '#F7F3E8'
PINE = '#17352C'
MINT = '#BDEFD4'
ORANGE = '#FF6B3D'
PEACH = '#FFB89D'
BUTTER = '#FFE7A3'
MUTED = '#5F6F68'
WHITE = '#FFFFFF'

FONT_DIR = Path('/root/marketplace/research/social-assets/fonts')
FRAUNCES = FONT_DIR / 'Fraunces-800.ttf'
FRAUNCES_SEMIBOLD = FONT_DIR / 'Fraunces-600.ttf'
DM = FONT_DIR / 'DMSans-500.ttf'
DM_BOLD = FONT_DIR / 'DMSans-700.ttf'
DM_REG = FONT_DIR / 'DMSans-400.ttf'

W = H = 1080
S = 2

def font(path, size):
    return ImageFont.truetype(str(path), size * S)

def pts_scale(points):
    return [(int(x*S), int(y*S)) for x,y in points]

def draw_bean(draw, cx, cy, width, fill=ORANGE, outline=PINE):
    # Compact hand-drawn bean mark. Deliberately simple so it survives avatar size.
    w = width
    h = width * 1.18
    box = [int((cx-w/2)*S), int((cy-h/2)*S), int((cx+w/2)*S), int((cy+h/2)*S)]
    draw.rounded_rectangle(box, radius=int(w*.42*S), fill=fill, outline=outline, width=max(3, int(w*.035*S)))
    r = max(3, int(w*.045*S))
    eye_y = int((cy-h*.07)*S)
    for ex in (cx-w*.16, cx+w*.16):
        draw.ellipse([int(ex*S-r), eye_y-r, int(ex*S+r), eye_y+r], fill=outline)
    # Small smile
    smile_box = [int((cx-w*.20)*S), int((cy+h*.02)*S), int((cx+w*.20)*S), int((cy+h*.29)*S)]
    draw.arc(smile_box, start=15, end=165, fill=outline, width=max(3, int(w*.032*S)))

def rounded_mask(size, radius):
    mask = Image.new('L', size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0,0,size[0]-1,size[1]-1], radius=radius, fill=255)
    return mask

def fit_art(src, box):
    x, y, w, h = box
    im = Image.open(src).convert('RGB')
    scale = max(w/im.width, h/im.height)
    im = im.resize((int(im.width*scale), int(im.height*scale)), Image.Resampling.LANCZOS)
    left = (im.width-w)//2
    top = (im.height-h)//2
    im = im.crop((left, top, left+w, top+h))
    mask = rounded_mask((w*S,h*S), int(26*S))
    im = im.resize((w*S,h*S), Image.Resampling.LANCZOS)
    return im, mask, (x*S, y*S)

def draw_tracking(draw, xy, text, fnt, fill, tracking=2.0):
    x, y = xy
    for ch in text:
        draw.text((int(x*S), int(y*S)), ch, font=fnt, fill=fill, anchor='la')
        x += draw.textlength(ch, font=fnt)/S + tracking
    return x

def center_text(draw, y, text, fnt, fill, max_width=None, line_gap=5):
    # Wrap only at explicit newline or spaces. Returns the final y.
    lines = text.split('\n')
    yy = y
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=fnt)
        width = (bbox[2]-bbox[0])/S
        draw.text((int((W-width)/2*S), int(yy*S)), line, font=fnt, fill=fill, anchor='la')
        yy += (bbox[3]-bbox[1])/S + line_gap
    return yy

def add_post(index, category, headline, subhead, chips, source):
    im = Image.new('RGB', (W*S,H*S), CREAM)
    d = ImageDraw.Draw(im)
    # Thin pine frame and a quiet offset rule: recognisable at a glance.
    d.rounded_rectangle([34*S,34*S,1046*S,1046*S], radius=28*S, outline=PINE, width=8*S)
    d.rounded_rectangle([50*S,50*S,1030*S,1030*S], radius=22*S, outline='#D9E2DC', width=2*S)
    # Header lockup
    draw_bean(d, 92, 92, 43)
    draw_tracking(d, (126, 78), 'OMO SPACE', font(DM_BOLD, 18), PINE, tracking=2.2)
    draw_tracking(d, (126, 104), category.upper(), font(DM_BOLD, 13), MUTED, tracking=2.3)
    # Orange index marker
    d.ellipse([969*S,74*S,1001*S,106*S], fill=ORANGE)
    d.text((985*S,90*S), f'{index:02d}', font=font(DM_BOLD, 13), fill=WHITE, anchor='mm')
    # Headline block
    hf = font(FRAUNCES, 57 if len(headline) < 25 else 49)
    sf = font(DM, 23)
    title_y = 153
    title_bottom = center_text(d, title_y, headline, hf, PINE, line_gap=0)
    sub_y = title_bottom + 14
    center_text(d, sub_y, subhead, sf, MUTED, line_gap=2)
    # Illustration card
    art_y = 365 if '\n' in headline else 340
    art_h = 465 if index in (1,4,5) else 490
    art_box = (90, art_y, 900, art_h)
    art, mask, pos = fit_art(source, art_box)
    # Drop shadow and card frame
    d.rounded_rectangle([84*S,(art_y+7)*S,996*S,(art_y+art_h+7)*S], radius=31*S, fill='#E6E5DD')
    im.paste(art, pos, mask)
    d.rounded_rectangle([90*S,art_y*S,990*S,(art_y+art_h)*S], radius=26*S, outline=PINE, width=5*S)
    # Chips / footer row
    chip_y = art_y + art_h + 34
    chip_font = font(DM_BOLD, 15)
    x = 90
    for txt, color in chips:
        tw = d.textlength(txt, font=chip_font)/S
        cw = tw + 40
        d.rounded_rectangle([x*S,chip_y*S,(x+cw)*S,(chip_y+42)*S], radius=21*S, fill=color, outline=PINE, width=2*S)
        d.text(((x+cw/2)*S,(chip_y+21)*S), txt, font=chip_font, fill=PINE, anchor='mm')
        x += cw + 12
    # Footer lockup
    d.line([90*S, 969*S, 990*S, 969*S], fill='#D9E2DC', width=2*S)
    d.text((90*S, 988*S), 'omo.space', font=font(DM_BOLD, 20), fill=PINE, anchor='lm')
    d.text((990*S, 988*S), 'BUY THE RESULT', font=font(DM_BOLD, 13), fill=ORANGE, anchor='rm')
    out = POSTS / f'{index:02d}-{category.lower().replace(" ", "-")}.png'
    im.resize((W,H), Image.Resampling.LANCZOS).save(out, quality=96)
    return out

def make_contact_sheet(paths):
    thumb = 540
    sheet = Image.new('RGB', (thumb*3, thumb*2), '#ECEDE8')
    d = ImageDraw.Draw(sheet)
    for i,p in enumerate(paths):
        x=(i%3)*thumb; y=(i//3)*thumb
        card = Image.open(p).convert('RGB').resize((thumb,thumb), Image.Resampling.LANCZOS)
        sheet.paste(card,(x,y))
    out=ROOT/'contact-sheet.png'
    sheet.save(out, quality=95)
    return out

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    POSTS.mkdir(parents=True, exist_ok=True)
    for src in SOURCES:
        if not src.exists():
            raise FileNotFoundError(src)
    specs = [
        ('Manifesto', 'Buy the result.\nNot another subscription.', 'Useful work should end in something you can keep.', [('PAY PER RUN', MINT), ('KEEP THE RESULT', BUTTER)], SOURCES[0]),
        ('How it works', 'Pick a workflow.\nAdd your inputs.', 'Omo turns a clear brief into a finished artifact.', [('PICK', MINT), ('RUN', PEACH), ('KEEP', BUTTER)], SOURCES[1]),
        ('Open source', 'Free to download.\nPay to host the run.', 'The recipe is yours. Omo charges for the useful execution.', [('OPEN SOURCE', MINT), ('HOSTED RUNS', PEACH)], SOURCES[2]),
        ('Marketplace', 'One marketplace.\nMany useful outcomes.', 'Books, charts, videos, documents — made by workflows that do a job.', [('BOOKS', MINT), ('CHARTS', BUTTER), ('VIDEO', PEACH)], SOURCES[3]),
        ('Brand statement', 'One prompt in.\nFinished work out.', 'Omo is the marketplace for useful AI workflows.', [('USEFUL AI', MINT), ('OMO SPACE', BUTTER)], SOURCES[4]),
    ]
    outputs=[]
    for i,spec in enumerate(specs, 1):
        outputs.append(add_post(i, *spec))
    make_contact_sheet(outputs)
    # Keep a local copy of the source illustrations for provenance and future iterations.
    srcdir=ROOT/'source-illustrations'
    srcdir.mkdir(exist_ok=True)
    for i,src in enumerate(SOURCES,1):
        shutil.copy2(src, srcdir/f'{i:02d}-source.png')
    print('\n'.join(str(p) for p in outputs))
    print(ROOT/'contact-sheet.png')

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import subprocess, textwrap, shutil

ROOT = Path('/root/marketplace/research/social-assets/reel-series-helpful-2026-08-19')
FONT_DIR = Path('/root/marketplace/research/social-assets/fonts')
BRAND = Path('/root/marketplace/research/social-assets/brand-launch-2026-08-17')
W, H, SCALE = 1080, 1920, 2

CREAM='#F8F7F5'; WARM='#F7F3E8'; PINE='#17352C'; MINT='#BDEFD4'; ORANGE='#FF6B3D'
PEACH='#FFB89D'; BUTTER='#FFE7A3'; MUTED='#5F6F68'; RULE='#D9E2DC'; WHITE='#FFFFFF'
DARK2='#0E241E'; DARK3='#21463B'; PALE='#EAF3EE'
FRAUNCES=FONT_DIR/'Fraunces-800.ttf'; FRAUNCES6=FONT_DIR/'Fraunces-600.ttf'
DM=FONT_DIR/'DMSans-400.ttf'; DM5=FONT_DIR/'DMSans-500.ttf'; DM7=FONT_DIR/'DMSans-700.ttf'
WARM_ART=BRAND/'source-illustrations/05-source.png'
TECH_ART=BRAND/'source-illustrations/03-source.png'

SERIES = [
 {
  'slug':'01-before-you-pay','mode':'warm','label':'BUYER CHECKLIST',
  'caption':'Before you pay for another AI tool, check the result, inputs, output format, failure behavior, and ownership. A clear workflow should make all five visible before you run it.',
  'slides':[
   ('hook','Before you pay for another AI tool,\ncheck these 5 things.','Most tools hide behind a blank chat box.'),
   ('1 / A FINISHED RESULT','The promise should name\nwhat you get.','An ad set. A PDF. A word list. A report.'),
   ('2 / CLEAR INPUTS','You should know what\nto provide before the run.','Good workflows do not make you guess what they need.'),
   ('3 / AN OUTPUT FORMAT','Ask what arrives\nat the end.','Text, JSON, PDF, ZIP, image, or video?'),
   ('4 / HONEST FAILURE','A trustworthy workflow\nexplains why it stopped.','It does not hide a missing step behind a confident guess.'),
   ('5 / A RESULT YOU KEEP','Download it. Edit it.\nUse it outside the tool.','Convenience is useful. Lock-in is not.'),
   ('takeaway','Save this checklist.','Useful AI should finish a job, not start another subscription.'),
  ]
 },
 {
  'slug':'02-pay-per-run-math','mode':'warm','label':'PRICE DECISION',
  'caption':'A subscription is right for a tool you use as a daily system. Pay per run is often better for a bounded job you need occasionally. This example uses Omo helpers priced at $0.10 per run.',
  'slides':[
   ('hook','A $20 subscription only makes sense\nif you use it.','Here is the simple math.'),
   ('THE ANNUAL COST','$20 per month\n= $240 per year.','You pay that even if you only need the tool twice.'),
   ('THE RUN COST','Twenty $0.10 runs\n= $2.','You pay for the work you actually use.'),
   ('THE BREAK-EVEN','200 runs per month.','At $0.10 per run, that is when $20 costs the same.'),
   ('SUBSCRIBE WHEN','The tool is part of\nyour daily system.','Frequent use can justify a recurring plan.'),
   ('PAY PER RUN WHEN','The job is bounded, occasional,\nand has a clear result.','Example: an ad set, a theme report, or a phonics word list.'),
   ('takeaway','Use this rule before you subscribe.','Daily system? Subscribe. Bounded job? Pay per run.\nExample uses Omo’s $0.10 helpers.'),
  ]
 },
 {
  'slug':'03-comments-to-decisions','mode':'warm','label':'CUSTOMER RESEARCH',
  'caption':'Do not turn a pile of comments into a confident summary. Clean the data, group the actual problems, keep supporting quotes, count carefully, and convert each theme into a specific action.',
  'slides':[
   ('hook','50 customer comments\nare not insight.','Do this before you act.'),
   ('STEP 1 / REMOVE NOISE','Delete duplicates, spam,\nand empty replies.','Remove personal data you do not need.'),
   ('STEP 2 / GROUP PAINS','Group comments by\nthe problem described.','Do not group them only because they repeat one word.'),
   ('STEP 3 / KEEP EVIDENCE','Save short quotes\nthat prove each theme.','A theme without evidence is only a guess.'),
   ('STEP 4 / COUNT CAREFULLY','Say “12 of 50 comments.”','Do not turn a small sample into “customers always say...”'),
   ('STEP 5 / TAKE ACTION','For each theme: fix one thing,\nexplain one thing, test one thing.','Make the next decision visible.'),
   ('takeaway','Need a first pass?','Omo’s Customer Feedback Theme Finder is $0.10/run.\nRead the evidence yourself before you act.'),
  ]
 },
 {
  'slug':'04-audit-skillmd','mode':'tech','label':'OPEN-SOURCE CHECKLIST',
  'caption':'Before you host a SKILL.md, define its inputs, output, access needs, cost limit, failure behavior, and proof. Unknown cost or missing capability should block the run instead of producing a guess.',
  'slides':[
   ('hook','Do not host a SKILL.md until you can\nanswer these 6 questions.','A prompt is not a production contract.'),
   ('01 / INPUTS','What are the inputs?','Types, size limits, required fields, and unsafe files.'),
   ('02 / OUTPUT','What is the exact output?','Name the file or schema. “Good result” is not a contract.'),
   ('03 / ACCESS','What access does it need?','List every secret, account, browser, and external service.'),
   ('04 / COST','What can one run cost?','Set a hard limit. Unknown cost is a blocker.'),
   ('05 / FAILURE','How does it stop safely?','Return a clear error and a resume point. Never hide a missing capability.'),
   ('06 / PROOF','What proves it works?','Run fixed test cases. Save the outputs. Check them.'),
   ('takeaway','Omo has a $5 hosting-candidate check.','It compiles and fixture-tests a candidate. It does not promise every SKILL.md can be hosted.'),
  ]
 },
 {
  'slug':'05-trustworthy-workflow','mode':'tech','label':'TRUST CHECKLIST',
  'caption':'A trustworthy AI workflow should name the job, show required inputs, define the output, explain the price, report limits, and show evidence. Use this checklist on every listing, including ours.',
  'slides':[
   ('hook','A trustworthy AI workflow\nis more than a prompt.','Check these six things before you run it.'),
   ('01 / THE JOB','It names one clear job.','“Make three fact-based ad variants” is clearer than “AI marketing helper.”'),
   ('02 / THE INPUTS','It shows what you must provide.','Required fields, file types, and size limits should be visible.'),
   ('03 / THE OUTPUT','It defines what you receive.','A file, schema, report, list, image, or video.'),
   ('04 / THE PRICE','It explains the run price.','You should know the cost before you press Run.'),
   ('05 / THE LIMITS','It reports what it cannot do.','A typed blocker is more trustworthy than a polished guess.'),
   ('06 / THE EVIDENCE','It shows tests or a real example.','Read the result. Do not trust a green badge alone.'),
   ('takeaway','If a listing hides these, do not buy it.','Use this checklist on every workflow — including ours.'),
  ]
 },
]

def F(path,size): return ImageFont.truetype(str(path), size*SCALE)

def rounded(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(tuple(int(v*SCALE) for v in box), radius=int(radius*SCALE), fill=fill, outline=outline, width=max(1,int(width*SCALE)))

def line(draw, box, fill, width=1): draw.line(tuple(int(v*SCALE) for v in box), fill=fill, width=max(1,int(width*SCALE)))

def text(draw, xy, s, f, fill, anchor='la', stroke=0, stroke_fill=None):
    draw.text((int(xy[0]*SCALE),int(xy[1]*SCALE)),s,font=f,fill=fill,anchor=anchor,stroke_width=int(stroke*SCALE),stroke_fill=stroke_fill)

def measure(draw,s,f): return draw.textbbox((0,0),s,font=f)[2]/SCALE

def wrap(draw, s, f, maxw):
    out=[]
    for para in s.split('\n'):
        words=para.split()
        if not words: out.append(''); continue
        cur=words[0]
        for w in words[1:]:
            cand=cur+' '+w
            if measure(draw,cand,f)<=maxw: cur=cand
            else: out.append(cur); cur=w
        out.append(cur)
    return out

def draw_wrapped(draw, s, f, fill, x, y, maxw, leading, anchor='la'):
    lines=wrap(draw,s,f,maxw)
    for ln in lines:
        text(draw,(x,y),ln,f,fill,anchor)
        y += leading
    return y

def bean(draw,cx,cy,w,fill=ORANGE,outline=PINE):
    rounded(draw,(cx-w/2,cy-w*.58,cx+w/2,cy+w*.58),w*.42,fill,outline,3)
    r=w*.045
    for ex in (cx-w*.15,cx+w*.15):
        draw.ellipse((int((ex-r)*SCALE),int((cy-w*.07-r)*SCALE),int((ex+r)*SCALE),int((cy-w*.07+r)*SCALE)),fill=outline)
    draw.arc((int((cx-w*.19)*SCALE),int((cy+w*.02)*SCALE),int((cx+w*.19)*SCALE),int((cy+w*.24)*SCALE)),15,165,fill=outline,width=max(3,int(w*.03*SCALE)))

def crop_art(path,w,h):
    im=Image.open(path).convert('RGB')
    scale=max(w/im.width,h/im.height)
    im=im.resize((int(im.width*scale),int(im.height*scale)),Image.Resampling.LANCZOS)
    l=(im.width-w)//2; t=(im.height-h)//2
    return im.crop((l,t,l+w,t+h))

def paste_round(canvas,art,box,radius):
    x,y,w,h=box
    art=art.resize((w*SCALE,h*SCALE),Image.Resampling.LANCZOS)
    mask=Image.new('L',(w*SCALE,h*SCALE),0); md=ImageDraw.Draw(mask)
    md.rounded_rectangle((0,0,w*SCALE-1,h*SCALE-1),radius=radius*SCALE,fill=255)
    canvas.paste(art,(x*SCALE,y*SCALE),mask)

def draw_header(draw,mode,label,idx,total):
    if mode=='warm':
        bean(draw,92,100,44)
        text(draw,(132,82),'OMO SPACE',F(DM7,18),PINE)
        text(draw,(132,111),label,F(DM7,12),MUTED)
        rounded(draw,(914,76,1000,120),22,ORANGE,None,0)
        text(draw,(957,98),f'{idx:02d}/{total:02d}',F(DM7,13),WHITE,'mm')
    else:
        rounded(draw,(66,64,1014,154),24,DARK2,CREAM,3)
        for i,c in enumerate((ORANGE,BUTTER,MINT)):
            draw.ellipse((int((92+i*34)*SCALE),int(92*SCALE),int((110+i*34)*SCALE),int(110*SCALE)),fill=c)
        text(draw,(214,108),'omo.space / workflow-check',F(DM7,16),CREAM,'lm')
        text(draw,(985,108),f'{idx:02d}/{total:02d}',F(DM7,14),MINT,'rm')
        text(draw,(68,194),label,F(DM7,13),MINT)

def draw_footer(draw,mode,slug):
    c=PINE if mode=='warm' else CREAM
    rule=RULE if mode=='warm' else DARK3
    line(draw,(70,1810,1010,1810),rule,2)
    text(draw,(70,1848),'omo.space',F(DM7,19),c,'lm')
    text(draw,(1010,1848),'BUY THE RESULT',F(DM7,13),ORANGE,'rm')

def warm_slide(slide,label,idx,total,slug):
    kind,title,body=slide
    im=Image.new('RGB',(W*SCALE,H*SCALE),CREAM); d=ImageDraw.Draw(im)
    rounded(d,(28,28,1052,1892),30,CREAM,PINE,8)
    rounded(d,(46,46,1034,1874),24,None,RULE,2)
    draw_header(d,'warm',label,idx,total)
    if kind=='hook':
        rounded(d,(70,210,1010,870),30,WARM,PINE,4)
        # Accent path and bean create the frame-one motion cue without covering copy.
        line(d,(650,820,810,760),ORANGE,10)
        bean(d,850,730,92)
        hf=F(FRAUNCES,75)
        draw_wrapped(d,title,hf,PINE,105,264,850,88)
        draw_wrapped(d,body,F(DM5,34),MUTED,106,706,790,48)
        art=crop_art(WARM_ART,900,650)
        paste_round(im,art,(90,945,900,650),28)
        d=ImageDraw.Draw(im)
        rounded(d,(90,945,990,1595),28,None,PINE,5)
        rounded(d,(112,1560,460,1620),30,ORANGE,PINE,2)
        text(d,(286,1590),'SAVE THIS',F(DM7,16),WHITE,'mm')
    elif kind=='takeaway':
        rounded(d,(70,240,1010,1590),34,MINT,PINE,5)
        bean(d,540,500,160)
        draw_wrapped(d,title,F(FRAUNCES,82),PINE,116,690,850,96)
        draw_wrapped(d,body,F(DM5,39),PINE,116,1000,840,56)
        rounded(d,(116,1390,964,1505),54,CREAM,PINE,3)
        text(d,(540,1448),'SAVE • SHARE • USE',F(DM7,22),PINE,'mm')
    else:
        rounded(d,(70,230,1010,1660),34,WHITE,PINE,5)
        text(d,(110,300),kind,F(DM7,18),ORANGE)
        draw_wrapped(d,title,F(FRAUNCES,83),PINE,110,370,840,96)
        # Helpful note block
        rounded(d,(110,930,970,1240),30,MINT,None,0)
        draw_wrapped(d,body,F(DM5,38),PINE,150,995,770,56)
        # A simple outcome shelf makes utility tangible without distracting.
        rounded(d,(110,1340,360,1510),24,BUTTER,PINE,3)
        rounded(d,(415,1340,665,1510),24,PEACH,PINE,3)
        rounded(d,(720,1340,970,1510),24,WARM,PINE,3)
        text(d,(235,1425),'INPUT',F(DM7,18),PINE,'mm')
        text(d,(540,1425),'RUN',F(DM7,18),PINE,'mm')
        text(d,(845,1425),'RESULT',F(DM7,18),PINE,'mm')
        line(d,(360,1425,415,1425),ORANGE,7); line(d,(665,1425,720,1425),ORANGE,7)
    draw_footer(d,'warm',slug)
    return im.resize((W,H),Image.Resampling.LANCZOS)

def tech_slide(slide,label,idx,total,slug):
    kind,title,body=slide
    im=Image.new('RGB',(W*SCALE,H*SCALE),PINE); d=ImageDraw.Draw(im)
    rounded(d,(28,28,1052,1892),30,PINE,CREAM,7)
    draw_header(d,'tech',label,idx,total)
    if kind=='hook':
        rounded(d,(66,250,1014,875),28,DARK2,MINT,3)
        text(d,(104,300),'$ CHECK / BEFORE_RUN',F(DM7,18),ORANGE)
        draw_wrapped(d,title,F(FRAUNCES,72),CREAM,104,375,840,86)
        draw_wrapped(d,body,F(DM5,32),MINT,104,745,820,46)
        art=crop_art(TECH_ART,900,620)
        paste_round(im,art,(90,960,900,620),28)
        d=ImageDraw.Draw(im); rounded(d,(90,960,990,1580),28,None,CREAM,4)
    elif kind=='takeaway':
        rounded(d,(66,260,1014,1585),30,DARK2,MINT,4)
        text(d,(104,320),'$ FINAL_CHECK',F(DM7,18),ORANGE)
        draw_wrapped(d,title,F(FRAUNCES,72),CREAM,104,430,820,86)
        rounded(d,(102,900,978,1370),26,DARK3,CREAM,2)
        draw_wrapped(d,body,F(DM5,34),PALE,142,980,790,52)
        text(d,(142,1320),'status: useful_and_honest',F(DM7,18),MINT)
    else:
        rounded(d,(66,250,1014,1605),30,DARK2,CREAM,3)
        text(d,(104,315),f'$ {kind.lower().replace(" / ","_").replace(" ","_")}',F(DM7,18),ORANGE)
        draw_wrapped(d,title,F(FRAUNCES,76),CREAM,104,420,820,90)
        rounded(d,(102,910,978,1280),24,DARK3,MINT,2)
        draw_wrapped(d,body,F(DM5,35),PALE,142,980,790,54)
        # code-like proof lines
        y=1390
        for k,v,c in [('contract','visible',MINT),('limit','explicit',BUTTER),('failure','typed',PEACH)]:
            text(d,(120,y),k,F(DM7,17),MUTED)
            text(d,(930,y),v,F(DM7,17),c,'ra')
            y+=62
    draw_footer(d,'tech',slug)
    return im.resize((W,H),Image.Resampling.LANCZOS)

def make_video(slide_paths,out):
    concat=out.with_suffix('.txt')
    lines=[]
    for i,p in enumerate(slide_paths):
        lines.append(f"file '{p.as_posix()}'")
        lines.append(f"duration {2.4 if i==len(slide_paths)-1 else 1.6}")
    lines.append(f"file '{slide_paths[-1].as_posix()}'")
    concat.write_text('\n'.join(lines)+'\n')
    cmd=['ffmpeg','-y','-f','concat','-safe','0','-i',str(concat),'-vf','fps=30,format=yuv420p','-c:v','libx264','-preset','medium','-crf','18','-movflags','+faststart',str(out)]
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    concat.unlink()

def contact_sheet(slides,out):
    tw,th=270,480; cols=4; rows=(len(slides)+cols-1)//cols
    sheet=Image.new('RGB',(tw*cols,th*rows),'#E8EAE4')
    for i,p in enumerate(slides):
        im=Image.open(p).convert('RGB').resize((tw,th),Image.Resampling.LANCZOS)
        sheet.paste(im,((i%cols)*tw,(i//cols)*th))
    sheet.save(out,quality=95)

def write_docs():
    lines=['# Omo helpful Reel series','',
      'Reference format: https://www.instagram.com/reel/DcCpNGpMTF8/','',
      'The reference was used for structure: a specific hook, fast vertical slides, one idea per frame, text readable without audio, a complete takeaway, and a final action. Its creator branding and face-led treatment were not copied.','',
      '## Brand modes','',
      '- Warm Living Utility (chosen style 5): posts 1–3.','- Open-source Terminal (chosen style 3): posts 4–5.','',
      '## Posts','']
    for p in SERIES:
        lines += [f"### {p['slug']}",p['caption'],'',f"Slides: {len(p['slides'])}. Reel duration: {((len(p['slides'])-1)*1.6+2.4):.1f} seconds. No audio is baked in so a platform-native sound can be selected later.",'']
    lines += ['## Publishing note','','These files are prepared only. Nothing was posted. Review every slide before publishing. Use the PNG slides for a carousel or the MP4 for a Reel.']
    (ROOT/'README.md').write_text('\n'.join(lines)+'\n')
    caps=['# Captions','']
    for i,p in enumerate(SERIES,1):
        caps += [f"## {i:02d} — {p['slug']}",p['caption'],'','Save this post if you want a clear checklist before your next run.','','#AIWorkflows #OpenSourceAI #OmoSpace','']
    (ROOT/'captions.md').write_text('\n'.join(caps)+'\n')

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    covers=[]
    for post in SERIES:
        pdir=ROOT/post['slug']; sdir=pdir/'slides'; sdir.mkdir(parents=True,exist_ok=True)
        paths=[]; total=len(post['slides'])
        for i,slide in enumerate(post['slides'],1):
            im=warm_slide(slide,post['label'],i,total,post['slug']) if post['mode']=='warm' else tech_slide(slide,post['label'],i,total,post['slug'])
            out=sdir/f'{i:02d}.png'; im.save(out,quality=96); paths.append(out)
        contact_sheet(paths,pdir/'contact-sheet.png')
        make_video(paths,pdir/f"{post['slug']}.mp4")
        covers.append(paths[0])
    # Series cover sheet
    sheet=Image.new('RGB',(1080,768),'#E8EAE4')
    for i,p in enumerate(covers):
        im=Image.open(p).convert('RGB').resize((216,384),Image.Resampling.LANCZOS)
        sheet.paste(im,(i*216,0))
    # Repeat lower half as larger previews of selected styles 3 and 5.
    for j,p in enumerate((covers[2],covers[4])):
        im=Image.open(p).convert('RGB').resize((384,384),Image.Resampling.LANCZOS)
        sheet.paste(im,(156+j*384,384))
    sheet.save(ROOT/'series-contact-sheet.png',quality=95)
    write_docs()
    print(f'Built {len(SERIES)} posts, {sum(len(p["slides"]) for p in SERIES)} slides')
    for p in SERIES: print(ROOT/p['slug']/f"{p['slug']}.mp4")

if __name__=='__main__': main()

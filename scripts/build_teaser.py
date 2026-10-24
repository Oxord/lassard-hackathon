"""Encode the six browser-rendered teaser cards into a 30-second silent MP4."""
from pathlib import Path
import subprocess
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT/'tmp/submission-build/qa'
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def run(args):
    result = subprocess.run([FFMPEG,'-hide_banner','-loglevel','error','-y',*args],capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stderr)


clips=[]
for i in range(6):
    frame=QA/f'teaser-{i}.png'
    assert frame.exists(),frame
    clip=QA/f'teaser-{i}.mp4'
    run(['-loop','1','-i',str(frame),'-t','5','-r','25','-vf','scale=1280:720,fade=t=in:st=0:d=0.3,fade=t=out:st=4.7:d=0.3','-c:v','libx264','-preset','medium','-crf','21','-pix_fmt','yuv420p','-an',str(clip)])
    clips.append(clip)
concat=QA/'teaser-concat.txt'
concat.write_text(''.join("file '"+p.as_posix()+"'\n" for p in clips),encoding='utf-8')
target=ROOT/'output/teaser.mp4'
run(['-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(target)])
info=imageio_ffmpeg.read_frames(str(target))
metadata=next(info);info.close()
assert metadata['size']==(1280,720),metadata
assert abs(metadata['duration']-30)<0.1,metadata
print({'file':str(target.relative_to(ROOT)),'size':metadata['size'],'duration':metadata['duration'],'bytes':target.stat().st_size})


ffmpeg -f concat -safe 0 -i <(for f in $PWD/freestyle?.mp4; do echo "file '$f'"; done) -c copy output.mp4

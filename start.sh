#!/run/current-system/sw/bin/bash
python ./main.py ./myConfig.json 0 \
  & python ./main.py ./myConfig.json 1 \
  & python ./main.py ./myConfig.json 2

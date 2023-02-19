#!/run/current-system/sw/bin/bash
./result/bin/qkm ./myConfig.json 0 \
  & ./result/bin/qkm ./myConfig.json 1 \
  & ./result/bin/qkm ./myConfig.json 2

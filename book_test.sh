#!/bin/bash

curl -i -v  -X POST https://qf5q-u9ak-080o.gw-1a.dockhost.net/api/bok \
    -H "Content-Type: application/json; charset=utf-8" \
    --data-binary '{
      "user_id": 67444034,
      "name": "Кирилл",
      "phone": "+79991234567",
      "date_time": "2025-10-05T10:00:00+01:00",
      "guests": 3
    }'
echo ''

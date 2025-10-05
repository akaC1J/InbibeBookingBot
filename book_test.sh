#!/bin/bash

  curl -i -X POST http://172.23.112.1:8000/api/book \
    -H "Content-Type: application/json; charset=utf-8" \
    --data-binary '{
      "user_id": 67444034,
      "name": "Кирилл",
      "phone": "+79991234567",
      "date_time": "2025-10-05T10:00:00+01:00",
      "guests": 3
    }'
echo ''

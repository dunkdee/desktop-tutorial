#!/bin/bash
LOGFILE="/home/dewayne/ai/logs/daily_content.log"
mkdir -p $(dirname $LOGFILE)

echo "==== $(date) Starting daily content automation ====" >> $LOGFILE

# Generate content
python3 /home/dewayne/ai/content_generator.py --type ebook >> $LOGFILE 2>&1
python3 /home/dewayne/ai/content_generator.py --type blog >> $LOGFILE 2>&1
python3 /home/dewayne/ai/content_generator.py --type video >> $LOGFILE 2>&1

# Push content
python3 /home/dewayne/ai/publish.py --platform gumroad >> $LOGFILE 2>&1
python3 /home/dewayne/ai/publish.py --platform youtube >> $LOGFILE 2>&1

echo "==== $(date) Daily content automation finished ====" >> $LOGFILE

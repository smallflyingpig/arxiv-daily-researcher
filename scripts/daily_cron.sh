#!/bin/bash
# ArXiv Daily Researcher - 每日定时任务

export PYTHONPATH=/home/jiguo/workspace/arxiv-daily-researcher
cd /home/jiguo/workspace/arxiv-daily-researcher

# 加载 conda 环境
source ~/miniconda3/etc/profile.d/conda.sh
conda activate arxiv-research

# 运行主程序
python main.py >> /home/jiguo/workspace/arxiv-daily-researcher/logs/cron.log 2>&1

# 记录执行时间
echo "=== Completed at $(date '+%Y-%m-%d %H:%M:%S') ===" >> /home/jiguo/workspace/arxiv-daily-researcher/logs/cron.log

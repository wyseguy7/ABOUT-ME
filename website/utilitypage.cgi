#!/home/rapiduser/miniconda3/envs/water_env/bin/python
from wsgiref.handlers import CGIHandler
from utilitypage.py import app

CGIHandler().run(app)
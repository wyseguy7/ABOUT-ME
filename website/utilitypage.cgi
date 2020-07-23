#!/home/rapiduser/miniconda3/envs/water_env/bin/python
from wsgiref.handlers import CGIHandler
from utilitypage import app

CGIHandler().run(app)
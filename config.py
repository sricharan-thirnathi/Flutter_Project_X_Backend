import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'ABC')
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://sricharan:charan%40123@projectx.wwbdqn9.mongodb.net/ProjectX?retryWrites=true&w=majority&appName=ProjectX')

# import os

# class Config:
#     SECRET_KEY = os.getenv('SECRET_KEY')
#     MONGO_URI = os.getenv('MONGO_URI')
import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'ABC')
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://preetham:37mDBDtI7YqBl6yq@projectx.wwbdqn9.mongodb.net/ProjectX?retryWrites=true&w=majority&appName=ProjectX')

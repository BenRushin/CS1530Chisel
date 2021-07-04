from flask import Flask, render_template, send_from_directory, session, request, redirect
from appbase import app, db
from models.Customer import Customer

@app.route('/')
def hello_world():
    return 'Hello, World!'
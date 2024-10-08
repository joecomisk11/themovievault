#!/usr/bin/env python3

from flask import Flask, request

app = Flask(__name__)

@app.route("/")
def main():
    return '''
     <h1>Echo Your Input</h1>
     <p>Please type something into the text box and click "Submit" to see it echoed back to you.</p>
     <form action="/echo_user_input" method="POST">
         <input name="user_input" placeholder="Type something here...">
         <input type="submit" value="Submit!">
     </form>
     '''

@app.route("/echo_user_input", methods=["POST"])
def echo_input():
    input_text = request.form.get("user_input", "")
    return "You entered: " + input_text

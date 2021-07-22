# CS1530Chisel

`python run.py` from root\
`pip install` any dependencies

>Should see something like:<br>
>Running on http://127.0.0.1:5000/<br>
>Open browser, type URL as, "localhost:5000"<br>
>And that should redirect to login page<br>

to record structural changes in the database:\
`pip install Flask-Migrate`\
`export FLASK_APP=chisel`\
`flask db migrate -m "message"`\
`flask db upgrade`

testing from root:\
`pip intall pytest`\
`pytest ./testing/`\
happy path test should succeed

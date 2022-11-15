from flask import Flask, request
from bs4 import BeautifulSoup
import mysql.connector
import requests

app = Flask(__name__)

base_url = 'https://en.wikipedia.org/wiki/'

config = {
    'user' : 'root',
    'password' : 'your_password', # <-- ADD ROOT PASSWORD HERE
    'host' : 'localhost',
    'database' : 'your_db' # <-- ADD LOCAL DATABASE HERE
}

def testForAccronym(word: str) -> bool:
    '''Tests for acronyms by seeing if all letters in a word are capitalised. Ignores two
    special cases: 'I', and 'A' at the start of a sentence.'''
    all_upper = True
    for letter in word:
        if not letter.isupper():
            all_upper = False

    if len(word) == 1:
        if word == 'A' or word == 'I':
            all_upper = False

    return all_upper

def getWebText(user_input: str) -> list:
    '''Pulls HTML data from a given URL and extracts only the text.'''
    response = requests.get(base_url + user_input)
    soup = BeautifulSoup(response.text, 'html.parser')

    website_text = ''
    for element in soup.find_all('p'):
        website_text += element.text

    #text processing
    website_text = ''.join(char for char in website_text if (char.isalpha() or char == ' ' or char == '\n')).replace('\n', ' ').split(' ')

    text_list = []
    for word in website_text:
        if not testForAccronym(word):
            word = word.lower()
            text_list.append(word)

    return text_list

def countFrequency(text_list: list) -> dict:
    '''Turns a list of words into a frequency dictionary.'''
    freq = {}
    for item in text_list:
        if (item in freq):
            freq[item] += 1
        else:
            freq[item] = 1

    return freq

def storeInRDS(text_list: list):
    '''Takes a list of words and makes all MySQL request to create tables and
    add a frequency table of the list to the database.'''
    freq_dict = countFrequency(text_list)
    freq_dict = sorted(freq_dict.items(), key=lambda kv: kv[1], reverse = True)
    
    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()

    try:
        cursor.execute('DROP TABLE wiki;')
        cnx.commit()
    except:
        pass

    try:
        cursor.execute('CREATE TABLE wiki (`word` VARCHAR(30), `freq.` INT);')
        cnx.commit()
    except:
        pass

    query = queryBuilder(freq_dict)

    try:
        cursor.execute(query)
    except mysql.connector.Error as err:
        print(err)

    cnx.commit

    cursor.execute('INSERT INTO wiki VALUES(null, null);')
    cnx.commit()
    cursor.close()
    cnx.close()

def queryBuilder(freq_dict: dict) -> str:
    '''Coverts elements of a frequency table into a MySQL insert query.'''
    query = 'INSERT INTO wiki VALUES '
    for element in freq_dict:
        query += "('" + str(element[0]) + "'," + str(element[1]) + '), '

    query += '(null, null);' # I don't know why this is needed but it won't run without this.

    return query

def mysqlRequest() -> list:
    '''Requests data from MySQL database and returns a proccessed tuple of the data.'''
    query = "SELECT * FROM wiki;"

    cnx = mysql.connector.connect(**config)
    cursor = cnx.cursor()
    
    cursor.execute(query)
    results = cursor.fetchall()

    cursor.close()
    cnx.close()

    data = dataProcessing(results)

    return data

def dataProcessing(data: list) -> tuple:
    '''Turns MySQL select data into a tuple of two list. One contains words and the
    other their frequency'''
    word_list = []
    freq_list = []

    for i in data:
        if i[0] != None:
            word_list.append(i[0])
            freq_list.append(i[1])

    return (word_list, freq_list)

@app.route('/')
def main():
    return '''
        <html>
        <head>
            <Title>Lab 2</Title>
            <style>
                body {
                    background-color: orange;
                    text-align: center;
                } 
            </style>
        </head>
        <body>
            <font face = "Comic Sans MS"> <div style="position:absolute; top:25%; left:50%; transform:translate(-50%, -50%);">
                <h1>CS3204 Welcome to my Lab 2 Web Application :) </h1>
            
                <h2>Enter the name of any English language Wikipedia article</h2>
                <h4>(e.g: 'United States of America', 'White-tailed deer', 'List of Sexually Active Popes')</h4>
                <h5>Note: ensure that titles are correctly spelled as they appear in the URL of pages</h5>
                <form action = "/submit" method="post">
                <input type = "text" name = "input">
                <input type = "Submit" value = "Submit">
                </form>
            </font></div>
        </body>
    </html>
    '''

@app.route('/submit', methods = ['POST'])
def web_scrape():
    user_input = request.form['input']
    user_input = user_input.replace(' ', '_') #convert user input to a usable form
    text_list = getWebText(user_input)
    storeInRDS(text_list)

    mysql_data = mysqlRequest()

    return f'''
        <html>
        <head>
            <title>Submit Page</title>
            <style>
                body {{
                    background-color: orange;
                    text-align: center;
                    font-family: Comic Sans MS;
                    position: absolute;
                    top: 25%%;
                    left: 50%%;
                }}
                #myDiv {{
                    display: table;
                    margin: 0 auto;
                }}
            </style>
        </head>
        <body>
            <h1>Results for the word distribution of the page "{user_input.replace('_', ' ')}"!</h1>
            <script src="https://cdn.plot.ly/plotly-1.5.1.min.js"></script>

                <div id="myDiv"></div>

                <script>
                var data = [
                {{
                    x: {mysql_data[0]},
                    y: {mysql_data[1]},
                    type: 'bar'
                }}
                ];

                Plotly.newPlot('myDiv', data);
            </script>
        </body>
    </html>
    '''

if __name__ == '__main__':
    app.run()
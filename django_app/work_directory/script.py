import os, requests, BeautifulSoup
url='./learn.html'
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')
print(soup.title.text) > output.txt

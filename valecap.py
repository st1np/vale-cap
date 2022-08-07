import requests
import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import aiohttp
import re
import json
from bs4 import BeautifulSoup
import lxml
from rich.pretty import pprint
import unicodedata
from copy import copy

class ValecapScraper():
  def __init__(self):
    self.antigo = 100
    self.regiao = ['aparecida', 'arapei', 'areias', 'bananal', 'cacapava', 'cachoeira paulista', 'campos do jordao', 'canas', 'caraguatatuba', 'cruzeiro', 'cunha', 'guaratingueta', 'igarata', 'ilhabela', 'jacarei', 'jambeiro', 'lagoinha', 'lavrinhas', 'lorena', 'monteiro lobato', 'natividade da serra', 'paraibuna', 'pindamonhangaba', 'piquete', 'potim', 'queluz', 'redencao da serra', 'roseira', 'santa branca', 'santo antonio do pinhal', 'sao bento do sapucai', 'sao jose do barreiro', 'sao jose dos campos', 'sao luiz do paraitinga', 'sao sebastiao', 'silveiras', 'taubate', 'tremembe', 'ubatuba']


    self.headers = {
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36'
    }
    self.data = {
      'sweepstake_date': '0',
      'action': 'capsadminwp_sweepstakes',
    }
    self.data['security'] = self.get_nonce()

    self.timeout = aiohttp.ClientTimeout(10)

    self.resultados = {}

  async def main(self):
    self.session = aiohttp.ClientSession()
    self.sem = asyncio.Semaphore(500)

    tasks = []
    self.sorteios_ids = []
    async with self.session:
      for sorteio_id in range(0,6600):
        tasks.append(asyncio.create_task(self.requests(sorteio_id)))
      await asyncio.gather(*tasks)
    
    with open('sorteios_ids.json', 'w') as f:
      json.dump(self.sorteios_ids, f)
    with open('sorteios_resultados.json', 'w') as f:
      json.dump(self.resultados, f)

  async def requests(self,sorteio_id):
    async with self.sem:
      try:
        async def req():
          data = copy(self.data)
          data['sweepstake'] = str(sorteio_id)
          async with self.session.post('https://valecaperegiao.com.br/wp-admin/admin-ajax.php', headers=self.headers, data=data) as resp:
            if resp.status == 200:
              content = await resp.text()
              if str(sorteio_id) == str(json.loads(content)['idSorteio']):
                if 'foi encontrado nenhum sorteio com a data informada' not in content.lower() and 'data do sorteio' in content.lower():
                  soup = BeautifulSoup(json.loads(content)['html'], 'lxml')

                  cidades = re.findall(r'(?<=)Cidade(.*?)(?=\<\/strong>)', str(soup.contents[0]))
                  cidades_regiao = []
                  for cidade in cidades:
                    try:
                      cidade = re.findall(r'(?<=)strong\>(.*?)(?=$)', cidade)[0].strip().lower()
                      cidade = self.remove_accents(cidade)
                    except:
                      cidade = None
                    if cidade in self.regiao:
                      cidades_regiao.append(cidade)
                      
                  if float(len(cidades_regiao)) >= float(len(cidades)) * 0.5 and len(cidades) != 0 and len(cidades_regiao) != 0:
                    try:
                      data = re.findall(r'(?<=Data do Sorteio: <strong>)(.*?)(?=<\/strong>)', str(soup.contents[0]))[0]
                    except:
                      print(re.findall(r'(?<=Data do Sorteio: <strong>)(.*?)(?=<\/strong>)', str(soup.contents[0])))
                      return

                    sorteios = soup.select('.sorteioItem')
                    if data not in self.resultados:
                      self.resultados[data] = {}
                      self.resultados[data]['id'] = sorteio_id
                      for sorteio in sorteios:
                        titulo = sorteio.select_one('.sorteioTitle').get_text()
                        if 'giro' in titulo.lower() or 'sorte' in titulo.lower():
                          continue

                        numeros_sorteados = [numero.get_text() for numero in sorteio.select('span.numberDicker')]
                        self.resultados[data][titulo] = numeros_sorteados
                      self.sorteios_ids.append(sorteio_id)
                      print(sorteio_id)
              else:
                if json.loads(content)['idSorteio'] != None:
                  await req()
            else:
              await req()
        await req()
      except:
        await req()

  def get_nonce(self):
    r = requests.get('https://valecaperegiao.com.br/resultados', headers=self.headers)
    nonce = re.findall(r'(?<="ajax_nonce":")(.*?)(?=")', r.text.encode("ascii", "ignore").decode("utf-8"))[0]
    return nonce
  
  def remove_accents(self, input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

asyncio.run(ValecapScraper().main())
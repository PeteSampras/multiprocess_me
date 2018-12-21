#!/usr/bin/env python

import sys
import requests
from bs4 import BeautifulSoup
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
from multiprocessing import Process, Queue, current_process, Manager
import multiprocessing
import numpy as np
import os

NUM_WORKERS = 4#multiprocessing.cpu_count()

# global variables
process_queue = Queue()
found_queue = Queue()
manager = Manager()
master_dict = manager.dict()
procs = []
my_logs = False

class MultiThreadScraper: # class does all processing

   def __init__(self, base_url,masterdict):
       self.base_url = base_url
       self.root_url = '{}://{}'.format(urlparse(self.base_url).scheme, urlparse(self.base_url).netloc)
       self.pool = ThreadPoolExecutor(max_workers=500) # was 50
       self.scraped_pages = set([])
       self.to_crawl = Queue()
       self.to_crawl.put(base_url)
       self.dict = masterdict

   def parse_links(self,html):
       soup = BeautifulSoup(html, 'html.parser')
       links = soup.find_all('a', href=True)
       for link in links:
           url = link['href']
           if url.startswith('//'):
               continue
           if url.startswith('/') or url.startswith(self.root_url):
               url = urljoin(self.root_url, url)
               if url not in self.scraped_pages:
                   self.to_crawl.put(url)
                   #print(url)
                   #found_queue.put(url)
                   self.dict.append(url)

   def scrape_info(self, html):
       return

   def post_scrape_callback(self, res):
       result = res.result()
       if result and result.status_code == 200:
           self.parse_links(result.text)
           self.scrape_info(result.text)

   def scrape_page(self, url):
       try:
           res = requests.get(url, timeout=(3, 10)) # was 30
           return res
       except requests.RequestException:
           return

   def run_scraper(self):
       while True:
           try:
               target_url = self.to_crawl.get(timeout=3) # was 60
               if target_url not in self.scraped_pages:
                   print("Scraping URL: {}".format(target_url))
                   self.scraped_pages.add(target_url)
                   job = self.pool.submit(self.scrape_page, target_url)
                   job.add_done_callback(self.post_scrape_callback)
           except Empty:
               return
           except Exception as e:
               print(e)
               continue

def get_listing(url):
    # headers = {
    #     'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'}
    html = None
    links = url
    if url.startswith('/'):
        url = website+url
    r = requests.get(url, timeout=3)   # was 10      
    if r.status_code == 200:
        html = r.text
        soup = BeautifulSoup(html, 'html.parser')
        listing_section = soup.findAll('a', href=True)
        links = [link['href'].strip() for link in listing_section]
        return links

def parse(links,master):
    for link in links:
        if link == "''":
            pass
        if link.startswith('//'):
            pass
        if link.startswith('mailto:'):
            pass
        if not link.startswith('//'):
            if link != '/' and not link.startswith('#') and '/' in link:
                if website in link:
                    master.append(link)
                if 'http' in link.lower() or 'www' in link.lower():
                    pass
                else:
                    master.append(link)
            else:
                pass
        pass
    return master

def chunks(n, page_list):
    """Splits the list into n chunks"""
    return np.array_split(page_list,n)

def threader(urls,master):
    for url in urls:
        s = MultiThreadScraper(url,master)
        s.run_scraper()

def start_scrape():
    global master_dict
    global procs

    # split urls up into chunks if more than one
    chunk = chunks(NUM_WORKERS,master_dict[0])

    # adjust actual size of processes if smaller to conserve cpu for threading
    size = NUM_WORKERS
    if len(master_dict[0]) < NUM_WORKERS:
        size = len(master_dict[0])

    # create all processes
    for i in range(size):
        x=i+1
        master_dict[x]=manager.list()
        print(chunk[i])
        p = Process(target=threader, args=(chunk[i],master_dict[x]))
        procs.append(p)
        p.start()

    global my_logs
    my_logs = True
    # join all created processes    
    for p in procs:
        p.join()
    print_menu()

def print_menu():
    options = ['\nMAIN MENU','Add domain','View domain list','Start processing queue','Stop processing queue','Display logs','Quit']
    print(options[0])
    for i in range(1,len(options)):
        print(str(i) + '. '+options[i])

def menu_options():
    c = None
    print_menu()
    while c == None:
        option = input ('Select an option: ')
        if option=='1': # add
            add()
        elif option=='2': # see list
            global master_dict
            print('Domains: {}'.format(master_dict[0]))
        elif option=='3': #'start'
            start_scrape()
        elif option=='4': #'stop'
            stop()
        elif option=='5': #'logs'
            logs()
        elif option=='6':
            os._exit(0)
        else:
            print('Error: Must select an avialable number.')

def stop():
    global procs
    print('Stopping all processes.')
    for p in procs:
        p.terminate()

def logs():
    global master_dict
    global my_logs

    if my_logs == False:
        print('No logs made yet.')
    else:
        for i in range(len(master_dict[0])):
            x = i+1
            a = master_dict[x]
            a=list(set(a))
            print('{}: {}'.format(master_dict[0][i],a))
    print_menu()

def add():
    global master_dict
    domain = input('Type domain to add:')
    if domain in master_dict[0]:
        print('{} is already added.'.format(domain))
    else:
        if not domain.startswith('http'):
            print('Domains must start with https')
            domain = 'https://'+domain
        master_dict[0].append(domain)
        print('{} successfully added'.format(domain))
    print('Domains: {}'.format(master_dict[0]))
    menu_options()


if __name__ == '__main__':
    # set up first dict
    master_dict[0] = manager.list()
    try:
        menu_options()
    except KeyboardInterrupt:
        print("Keyboard interrupted")
    except Exception as e:
        print(e)
    finally:
        print('Script ended. Exiting.')
        os._exit(0)
    

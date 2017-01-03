# pylint: disable=C0103
import re
from lxml import html
from lxml.html.soupparser import fromstring
from lxml.cssselect import CSSSelector
import requests
import requests_cache
import pprint

requests_cache.install_cache('govindia', backend='sqlite', allowable_methods=('GET', 'POST'))


bodies = {
    'Union Government': 'http://goidirectory.gov.in/union_index.php',
    'States & Union Territories': 'http://goidirectory.gov.in/state.php',
    'Legislature': 'http://goidirectory.gov.in/legislature_index.php',
    'Judiciary': 'http://goidirectory.gov.in/judiciary_index.php'
}
base_url = 'http://goidirectory.gov.in'

'''
Disable this for now.
#Right now we only care about Union Govt
page = requests.get(bodies['Union Government'])

#Fetch the categories eg. Apex Bodies, Committees etc.
tree = html.fromstring(page.content)

bodies = CSSSelector('h2.inner_blockhead > a')(tree)
parsed_bodies = []
re_get_args = re.compile("(?:'(.+?)'.*?)+")

# Get the list of categories.
for body in bodies:
    p_body = {}
    p_body['name'] = body.text_content()
    cat_name_string = re_get_args.findall(body.attrib['href'])
    p_body['cat_id'] = cat_name_string[0]
    p_body['cat_name'] = cat_name_string[1]
    parsed_bodies.append(p_body)'''

'''
Unfortunately had to gather manually.
To use these urls we have to append the category id to these urls in the "ct" parameter for everything except for the union_apex category.
Also need to get ministries_index.php as a beter alternative to union_categories.php, or maybe ministries_departments_view.php
for ministries_index it has to be a POST request with the required ministry value to get the list of sub-categories
from there we can fetch the required IDs of the sub categories to submit to the atoz page - which gives the list of sites.
'''

scrape_urls = {
    'E001': 'union_apex.php',
    'E002': 'union_categories.php',
    'E053': 'union_categories.php',
    'E009': 'union_organisation.php',
    'E013': 'union_organisation.php',
    'E007': 'union_organisation.php'
}

def get_organizations(categ_id):
    payload = {
        "categ_id": categ_id,
        "categ_name": "Commissions%2FCommittees%2FMissions",
        "minid": None,
        "minname": None,
        "search_id": "bothGov",
        "form_id": "union",
        "formname1": "union",
        "category": "title",
        "pageno": None,
        "gid": "ug",
        "catid": categ_id,
        "tellafriend_url": None,
        "textsize1": None,
        "contrastscheme1": None,
        "orgnsation_name": None,
        "categ_id_newadd": None,
        "stateid_newadd": None,
        "perform_action": None,
        "search_text": None
    }
    page = requests.post('{}/{}'.format(base_url,scrape_urls[categ_id]), params={'ct':categ_id}, data=payload)
    total_pages = howmany_pages(page)
    all_parsed_links = []
    #Iterate all available pages
    for i in range(1,total_pages+1):
        payload['pageno'] = str(i)
        page = requests.post('{}/{}'.format(base_url,scrape_urls[categ_id]), params={'ct':categ_id}, data=payload)
        all_parsed_links.extend(parse_page(page))
    pprint.pprint(all_parsed_links)
        
    

def howmany_pages(page):
    tree = html.fromstring(page.content)
    pagenos = tree.cssselect('div.pagination > ul > li')
    return len(pagenos) - 1

def get_apex():
    #Need the entire empty payload - wont work otherwise for some reason.
    payload = {
        'categ_id': '',
        'categ_name': 'Apex Bodies',
        'search_id':'bothGov',
        'form_id':'union',
        'formname1':'union',
        'category':'title',
        'gid':'ug',
        'catid':'E001',
        'list_all':'all',
        'pageno':'',
        'tellafriend_url':'',
        'textsize1':'',
        'contrastscheme1':'',
        'orgnsation_name':'',
        'categ_id_newadd':'',
        'stateid_newadd':'',
        'perform_action':'',
        'search_text':''
    }
    page = requests.post('{}/{}'.format(base_url,scrape_urls['E001']), data=payload)
    parse_page(page)

def extract_link_title(a_element):
    #Need to checkout the title element;
    if(a_element.text_content()):
        return {
            'title': a_element.text_content(),
            'link': a_element.attrib['title'].split('-')[0].strip()
        }
    else: return None

'''
    sub_link_object = {
        'title':'',
        'link':''
        'children':['<optional>' - 1 or more sub_link_object]
    }
'''
def parse_page(page):
    tree = html.fromstring(page.content)
    bodies = tree.cssselect('div.inner_mid_container > ul > li')
    parsed_bodies = []
    re_get_args = re.compile("(?:'(.+?)'.*?)+")
    for body in bodies:
        sub_link_object = {}
        #Main Site - Fetch HREF
        main_a_element = body.findall('a')[-1]
        main_link_title = extract_link_title(main_a_element)
        if(main_link_title):
            sub_link_object = main_link_title
            #Children - Iterate and add to Dict
            sub_a_elements = body.cssselect('ul > li')
            if(sub_a_elements):
                sub_link_object['children'] = []
                for sub_body in sub_a_elements:
                    child_link_object = {}
                    sub_element = sub_body.findall('a')[-1]
                    child_link_object = extract_link_title(sub_element)
                    if(child_link_object):
                        sub_link_object['children'].append(child_link_object)
            parsed_bodies.append(sub_link_object)
    return parsed_bodies #pprint.pprint(parsed_bodies)

def get_everything():
    get_apex()
    get_organizations('E009')
    get_organizations('E007')
    get_organizations('E013')
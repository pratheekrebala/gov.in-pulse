# pylint: disable=C0103
import re
from lxml import html
from lxml.html.soupparser import fromstring
from lxml.cssselect import CSSSelector
import requests
import requests_cache
import pprint
import simplejson as json
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
    return all_parsed_links
        
    

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
    return parse_page(page)

#def parse_list():
    #Check for A element to set the title & link
    #This is the "Parent" element
    #Find ul element to signify presence of children
    #If children are present (i.e ul element) then iterate through each li element.
    #each li element goes through same parse_list() function to set the same properties.

def get_ministries():
    #Get all available ministries
    page = requests.get('{}/{}'.format(base_url, scrape_urls['E002']), params={'ct':'E002'})
    tree = html.fromstring(page.content)
    ministries = tree.cssselect('div.inner_mid_container li')
    ministry_array = []
    for ministry in ministries:
        min_a_element = ministry.cssselect('a.heading_small_url')[-1]
        curr_ministry = {}
        curr_ministry = extract_link_title(min_a_element, href=True)
        if(curr_ministry):
            print(curr_ministry)
            ministry_array.append(curr_ministry)
    #Iterate through the ministries above to hit the ministries_categories.php page.
    ministry_info_page = 'ministries_categories.php'
    pprint.pprint(ministry_array)
    parsed_ministries = []
    for ministry in ministry_array:
        ministry_id = ministry['link'][0]
        print("Fetching {} with id: {}".format(ministry['title'], ministry['link'][0]))
        page = requests.get('{}/{}'.format(base_url, ministry_info_page), params={'ct':ministry_id})
        tree = html.fromstring(page.content)
        #Of the available list elements
        #4 lists implies that first list is the ministry (ignore), sub-departments (ignore)
        # we care about bodies directly under ministry and finally the department list.
        # If there are only two - ignore the first and look at the second.
        # If there are three then ignore the first and look at the last two.
        lists_on_page = tree.cssselect('div.inner_mid_container > div.scroll_div > ul > li')[1:]
        ministry_obj = extract_link_title(lists_on_page[0].find('a'))#.text_content().strip()
        if len(lists_on_page) == 3:
            #We need to skip one list because we don't want the individual departments. instead load them from the next list.
            non_dept_list = 2
        elif len(lists_on_page) > 1: non_dept_list = 1
        else: non_dept_list = 0
        ministry_children = lists_on_page[non_dept_list].cssselect('ul > li.minstries_heading')
        #print(ministry_title, parse_ministry_child(lists_on_page[0]))
        ministry_obj['children'] = []
        for child in ministry_children:
            if non_dept_list == 0:
                sub_category_title = child.cssselect('div > a')[-1].text_content().strip()
                sub_category_children = parse_child(child.find('ul'))
                sub_category_obj = {'title': sub_category_title, 'link': 'None', 'children': sub_category_children}
                ministry_obj['children'].append(sub_category_obj)
                #print(len(lists_on_page), ministry_title, sub_category_title, sub_category_children, '\n')
            elif child.text_content().strip():
                if child.cssselect('div.ti'):
                    #Then this is a heading for the department.
                    department_obj = extract_link_title(child.cssselect('div.ti > a')[-1])#.text_content().strip()
                    department_obj['children'] = []
                else:
                    #This is the list containing the children of the above element.
                    sub_category_title = child.cssselect('div > a')[-1].text_content().strip()
                    sub_category_children = parse_child(child.find('ul'))
                    department_obj['children'].append({'title': sub_category_title, 'link': 'None', 'children': sub_category_children})
                ministry_obj['children'].append(department_obj)
                    #print(len(lists_on_page), ministry_title, department_name, sub_category_title, sub_category_children, '\n')
        parsed_ministries.append(ministry_obj)
    return parsed_ministries
    '''for child in ministries_children:
            sub_category_title = child.cssselect('div.min_sub_grp_name > a')[-1].text_content().strip()
            sub_category_elements = parse_child()
        for l in lists_on_page:
            if(l.text_content()):
                if l.find('a') is not None: curr_title = l.find('a').text_content().strip()
                print(ministry_id, ministry_title, curr_title)'''

re_get_args = re.compile("(?:'(.+?)'.*?)+")
def extract_link_title(a_element, href=False):
    #Need to checkout the title element;
    if(a_element.text_content()):
        if href:
            link = tuple(re_get_args.findall(a_element.attrib['href']))
        else: link = a_element.attrib['title'].split('-')[0].strip() if 'title' in a_element.attrib else 'Missing Link'
        return {
            'title': a_element.text_content().strip(),
            'link': link
        }
    else: return None

'''
    sub_link_object = {
        'title':'',
        'link':''
        'children':['<optional>' - 1 or more sub_link_object]
    }
'''

def parse_ministry_child(parent):
    children = []
    sub_a_elements = parent.cssselect('ul > li')
    if (sub_a_elements):
        for sub_body in sub_a_elements:
            if sub_body.text_content().strip():
                child_link_object = {}
                sub_element = sub_body.cssselect('div.min_sub_grp_name > a')[-1]
                print(sub_element.text_content())
                #print(sub_body.text_content().strip())

def parse_child(parent):
    children = []
    sub_a_elements = parent.cssselect('ul > li')
    if(sub_a_elements):
        for sub_body in sub_a_elements:
            child_link_object = {}
            sub_element = sub_body.findall('a')[-1]
            child_link_object = extract_link_title(sub_element)
            #Check for sub-links - worried about recursion here but good for now.
            child_elements = parse_child(sub_body)
            if(child_elements):
                child_link_object['children'] = child_elements
            if(child_link_object):
                children.append(child_link_object)
        return children
    else: return None
    
def parse_page(page):
    tree = html.fromstring(page.content)
    bodies = tree.cssselect('div.inner_mid_container > ul > li')
    parsed_bodies = []
    for body in bodies:
        sub_link_object = {}
        #Main Site - Fetch HREF
        main_a_element = body.findall('a')[-1]
        main_link_title = extract_link_title(main_a_element)
        if(main_link_title):
            sub_link_object = main_link_title
            #Children - Iterate and add to Dict
            sub_children = parse_child(body)
            if(sub_children):
                sub_link_object['children'] = sub_children
            parsed_bodies.append(sub_link_object)
    return parsed_bodies #pprint.pprint(parsed_bodies)

def get_everything():
    return {'apex': get_apex(),
    'academies': get_organizations('E009'),
    'autonomous':get_organizations('E007'),
    'commissions': get_organizations('E013'),
    'ministries': get_ministries()}

fd = open('./data/goi_directory.json', 'w')
fd.write(json.dumps(get_everything()))
fd.close()
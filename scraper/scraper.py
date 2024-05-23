# -*- coding: utf-8 -*-
from scraper.googlemaps import GoogleMapsScraper
from datetime import datetime, timedelta
import argparse
import csv
from termcolor import colored
import time


ind = {'most_relevant' : 0 , 'newest' : 1, 'highest_rating' : 2, 'lowest_rating' : 3 }
HEADER = ['id_review', 'caption', 'relative_date', 'retrieval_date', 'rating', 'username', 'n_review_user', 'n_photo_user', 'url_user']
HEADER_W_SOURCE = ['id_review', 'caption', 'relative_date','retrieval_date', 'rating', 'username', 'n_review_user', 'n_photo_user', 'url_user', 'url_source']

def csv_writer(source_field, ind_sort_by, path='data/'):
    outfile= ind_sort_by + '_gm_reviews.csv'
    targetfile = open(path + outfile, mode='w', encoding='utf-8', newline='\n')
    writer = csv.writer(targetfile, quoting=csv.QUOTE_MINIMAL)

    if source_field:
        h = HEADER_W_SOURCE
    else:
        h = HEADER
    writer.writerow(h)

    return writer

def scrape_for_reviews(debug, N, url, sort_by):
    total_reviews = []
    with GoogleMapsScraper(debug=False) as scraper:
        if False: #args.place:
            print(scraper.get_account(url))
        else:
            error = scraper.sort_by(url, ind[sort_by])

            if error == 0:

                n = 0

                if ind[sort_by] == 0:
                   scraper.more_reviews()

                while n < N:

                    # logging to std out
                    print(colored('[Review ' + str(n) + ']', 'cyan'))

                    reviews = scraper.get_reviews(n)
                    
                    if len(reviews) == 0:
                        break
                    
                    total_reviews.append(reviews)

                    n += len(reviews)
    return {"reviews": total_reviews}



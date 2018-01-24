# -*- coding: utf-8 -*-

import scrapy
from time import sleep
from random import randint
from urllib.parse import urljoin

class RentalSpider(scrapy.Spider):
    name = 'seattle'

    start_urls = ['https://seattle.craigslist.org/search/apa?s=120&availabilityMode=0&postedToday=1']

    def parse(self, response):
        #only grab one line
        for href in response.css('.hdrlnk').xpath('@href').extract():
            #sleep(randint(1,63)*0.01)
            yield response.follow(href, self.parse_listing)

        next_page = response.css('.next').xpath('@href').extract_first()
        readuntil = int(response.css('.rangeTo::text').extract_first())
        #if readuntil<600:
        if response.css('.rangeTo::text').extract_first()!=response.css('.totalcount::text').extract_first() and response.css('.pagenum::text').extract_first()!='no results':
            #yield response.follow(next_page, self.parse_listing)
            #sleep(randint(10,25))
            #sleep(randint(1,63)*0.01)
            yield response.follow(urljoin('https://seattle.craigslist.org/',next_page), self.parse)

    def parse_listing(self, response):
        def extract_with_css(query):
            return response.css(query).extract_first().strip()

        yield {
            'price': extract_with_css('.price::text'),
            'neighborhood': extract_with_css('small::text'),
            'address': extract_with_css('.mapaddress::text'),
            'latitude': response.css('#map').xpath('@data-latitude')
                                     .extract_first().strip(),
            'longitude': response.css('#map').xpath('@data-longitude')
                                     .extract_first().strip(),
            'body': response.css('#postingbody::text').extract(),
            'postid': response.css('.postinginfo::text').re(r'post id:\s*(.*)')
        }

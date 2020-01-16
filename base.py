import io
import logging
import requests
import xml.etree.ElementTree as ET
from abc import ABCMeta, abstractmethod
from requests.exceptions import HTTPError

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


class ResponseHandler:
    """
    Class implementing a response processing decorator
    """
    @classmethod
    def handler(cls, func):
        def wrapper(*args, **kwargs):
            try:
                response = func(*args, **kwargs)
                response.raise_for_status()
            except HTTPError as http_error:
                logging.warning(f'{http_error} - Issue with request')
            except Exception as exc:
                logging.warning(f'{exc} - issue in program')
            else:
                return response
        return wrapper


class Tracktor(metaclass=ABCMeta):
    """
    Base class implementing main methods for parser classes
    """
    @abstractmethod
    def _make_request(self, *args, **kwargs):
        """
        Request method in subclasses to get tracking information
        :return: request.response object
        """
        pass

    @ResponseHandler.handler
    def track(self, *args, **kwargs):
        """
        Main method that should be called by any child class
        :param args: args from child._make_request
        :param kwargs: kwargs from child._make_request
        :return: result from child._make_request method
        """
        return self._make_request(*args, **kwargs)


class UpsTracktor(Tracktor):
    """
    Class for UPS tracking numbers information gathering
    """
    def __init__(self):
        self.url = 'https://www.ups.com/track/api/Track/GetStatus?loc=en_US'
        self.body = {
            'Locale': 'en_US',
            'Requester': 'wt/trackdetails'
        }
        self.headers = {
            'accept': "application/json, text/plain, */*",
            'content-type': "application/json",
    }

    def _make_request(self, tracking_numbers: list):
        """
        Retrieve data about tracking's from UPS web-site
        :param tracking_numbers: list of strings
        :return: request.response object (response body is json-like data)
        """
        self.body.update(dict(TrackingNumber=tracking_numbers))
        return requests.post(url=self.url, data=str(self.body), headers=self.headers)


class UspsTracktor(Tracktor):
    """
    Class for USPS tracking numbers information gathering
    Use official API:
        https://www.usps.com/business/web-tools-apis/#api
    """
    def __init__(self, user_id: str):
        """
        :param user_id: user id from Web Tools API(free registration)
        """
        self.user_id = user_id
        self.url = 'http://production.shippingapis.com/ShippingAPI.dll'
        self.params = {
            'API': 'TrackV2'
        }

    def _build_xml(self):
        """
        Method to build xml for the request(according API documentation)
        :return: xml string
        """
        builder = ET.TreeBuilder()
        builder.start('TrackRequest', {'USERID': self.user_id})    # start root node

        for tracking_number in self.tracking_numbers:              # add node with each tracking number
            builder.start('TrackID', {'ID': tracking_number})
            builder.end('TrackID')

        builder.end("TrackRequest")                                # close root node
        root = builder.close()                                     # close builder

        temp_buffer = io.BytesIO()                                 # create byte stream buffer
        ET.ElementTree.write(ET.ElementTree(root), temp_buffer, xml_declaration=True, encoding="UTF-8",
                             short_empty_elements=False)           # Write full built xml to the temp_buffer

        return temp_buffer.getvalue().decode('utf-8')

    def _make_request(self, tracking_numbers: list):
        """
        Retrieve data about tracking's from UPS web-site
        :param tracking_numbers: list of strings
        :return: request.response object (response body is xml-like data)
        """
        self.tracking_numbers = tracking_numbers
        self.params['XML'] = self._build_xml()
        return requests.get(url=self.url, params=self.params)


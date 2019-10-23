"""
API for the Charite Lernzielplatform. Uses requests and lxml for scraping the
website.
"""
import re
from dataclasses import dataclass

import requests
from lxml import html

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:69.0) Gecko/20100101 Firefox/69.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://lernziele.charite.de/zend/login/loginstudierende',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
}


class LernzielSession:
    base_url = "https://lernziele.charite.de/zend"

    def __init__(self):
        self._session = requests.Session()

    def login(self, user, password):
        data = {
            "user": user,
            "pass": password,
            "login": "Login",
        }
        response = self._session.post(
            self.base_url + "/login/loginstudierende",
            headers=HEADERS,
            data=data)
        response.raise_for_status()
        if "Login fehlgeschlagen!" in response.text:
            raise RuntimeError("Login failed")
        return self

    def get(self, path, params):
        response = self._session.get(self.base_url + path, params=params)
        response.raise_for_status()
        return html.document_fromstring(response.text)

    def post(self, path, data):
        response = self._session.post(self.base_url + path, data=data)
        response.raise_for_status()
        return html.document_fromstring(response.text)


class Scraper:
    session = None
    url = ""
    term = "WiSe2019"
    study = "Modellstudiengang2"
    grade = "ind"
    table_header = ""
    table_body = ""
    table_row_fields = {}

    def __init__(self, term="WiSe2019", grade="ind", session=None):
        """
        Args:
            semester: Semester time, such as SoSe2019, or other
            grade: Grade, such as 1st, 2nd or 3rd.
        """
        self.term = term
        self.grade = grade
        self.session = session

    def attach(self, session):
        self.session = session
        return self

    def _extract_table(self, page):
        control_elem = page.xpath(
            "//div[contains(@class, 'paginationControl')]")[0]
        control_text = control_elem.text.strip()
        match = re.match("(\d+) - (\d+)\s+von (\d+) Elementen", control_text)
        # start = match[1]
        end = match[2]
        total = match[3]

        colnames = [
          node.text_content()
          for node in page.xpath(self.table_header)
        ]

        items = []
        for row in page.xpath(self.table_body):
            content = [cell.text_content().strip() for cell in row.xpath("td")]
            item = dict(zip(colnames, content))
            for field_name, field_path in self.table_row_fields.items():
                link = row.xpath(field_path)[0]
                item_id = link.get("href").split("/")[-1]
                item[field_name] = item_id
            items.append(item)
        return items, end, total

    @staticmethod
    def build_study_url(study, term, grade):
        return f"/studiengang/{study}/zeitsemester/{term}/fachsemester/{grade}"

    def build_url(self, page=0):
        type_url = self.url
        study_url = self.build_study_url(self.study, self.term, self.grade)
        if page != 0:
            study_url += "/page/0"
        return type_url + study_url

    def get_data(self):
        raise NotImplementedError


@dataclass(eq=True, frozen=True)
class Event:
    id: str
    module: str
    week: str
    type: str
    title: str


@dataclass(eq=True, frozen=True)
class Lernziel:
    id: str
    event: Event
    type: str
    text: str


class LernzielScraper(Scraper):
    url = "/studentenlernziele/index"

    table_header = "/html/body/div[4]/table[2]/tr[1]/td"
    table_body = "/html/body/div[4]/table[2]/tr[position() > 1]"
    table_row_fields = {
        "LernzielId": "td[7]/ul/li/a[1]",
        "EventId": "td[3]/ul/li/a",
    }

    def _create_from_table_row(self, rowdata: dict):
        event = Event(
            id=rowdata["EventId"],
            module=rowdata["Modul"],
            week=rowdata["Woche"],
            type=rowdata["Veranstaltung"],
            title=rowdata["Titel"],
        )
        return Lernziel(
            id=rowdata["LernzielId"],
            event=event,
            type=rowdata["Lernziel-dimension"],
            text=rowdata["Lernziel – Die Studierenden sollen…"]
        )

    def get_data(self, page=0):
        page = self.session.get(
            self.build_url(page=page), params={"itemsPerPage": "1000"})

        items, end, total = self._extract_table(page)

        items = [self._create_from_table_row(i) for i in items]

        if end < total:
            items += self.get_data(page=page + 1)

        return items


class EventScraper(Scraper):
    url = "/plan/list"

    table_header = "/html/body/div[4]/table[3]/tr[1]/td"
    table_body = "/html/body/div[4]/table[3]/tr[position() > 1]"

    table_row_fields = {
        "EventId": "td[1]/ul/li/a",
    }

    def _create_from_table_row(self, rowdata):
        raw_title = rowdata["Veranstaltung"]
        type, title = raw_title.split(": ", 1)
        type = type.strip()
        title, module_week = title.rsplit(" (", 1)
        module, week = module_week.strip(")").split(", ")
        return Event(
            id=rowdata["EventId"],
            module=module,
            type=type,
            week=week,
            title=title,
        )

    def get_data(self, page=0):
        page = self.session.get(
            self.build_url(page=page), params={"itemsPerPage": "1000"})

        items, end, total = self._extract_table(page)

        items = [self._create_from_table_row(i) for i in items]

        if end < total:
            items += self.get_data(page=page + 1)

        return items

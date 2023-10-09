from typing import Any

from modules.library import Library
from functools import cached_property
from modules import builder, util
import requests

from modules.util import Failed

logger = util.logger

library_types = ["movies", "Music", "TV Shows"]

library_get_items_type = {
    "movies": "Movie",
    "tvshows": "Series",
}


class SystemInfo:

    def __init__(self, json):
        self.version = json["Version"]
        self.server_name = json["ServerName"]



class EmbyItem:

    def __init__(self, json):
        self.ratingKey = json["Id"]
        self.title = json["Name"]
        # TODO: add guid ???

class EmbyServer:

    def __init__(self, url, token, user_id):
        self.url = url
        self.token = token
        self.user_id = user_id
        self.machineIdentifier = ""
        self.client = requests.Session()
        self.info = SystemInfo(self.get("/System/Info"))
        self.library = self.get("/Library/MediaFolders")["Items"]
        self.version = self.info.version

    @cached_property
    def get_info(self):
        s_info = self.get("/System/Info")
        return SystemInfo(s_info)

    @cached_property
    def get_library(self):
        return self.get("/Library/MediaFolders")

    def get(self, path, params=None, headers=None) -> Any:
        url = self.url + path

        if headers is None:
            headers = {}
        headers["X-Emby-Token"] = self.token
        response = self.client.get(url, headers=headers, params=params)
        return response.json()


class Emby(Library):

    def notify(self, text, collection=None, critical=True):
        self.config.notify(text, server=self.EmbyServer.info.server_name, critical=critical)

    def notify_delete(self, message):
        self.config.notify_delete(message, server=self.EmbyServer.info.server_name, library=self.name)

    def _upload_image(self, item, image):
        pass

    def upload_poster(self, item, image, url=False):
        pass

    def image_update(self, item, image, tmdb=None, title=None, poster=True):
        pass

    def reload(self, item, force=False):
        pass

    def edit_tags(self, attr, obj, add_tags=None, remove_tags=None, sync_tags=None, do_print=True, locked=True,
                  is_locked=None):
        pass

    def item_labels(self, item):
        pass

    def find_poster_url(self, item):
        pass

    def item_posters(self, item, providers=None):
        pass

    def get_all(self, builder_level=None, load=False):
        if load and builder_level in [None, "show", "artist", "movie"]:
            self._all_items = []
        if self._all_items and builder_level in [None, "show", "artist", "movie"]:
            return self._all_items

        builer_type = builder_level if builder_level else self.type
        if not builder_level:
            builder_level = self.type

        logger.info(f"Loading All {builder_level.capitalize}s from Emby Library: {self.name}")
        results = []
        total_size = 1
        container_start = 0
        container_size = 50
        while total_size > len(results) and container_start <= total_size:
            data = self.EmbyServer.get(
                f"/Users/{self.EmbyServer.user_id}/Items?includedItemTypes={library_get_items_type[self.type]}&ParentId={self.Emby['Id']}&StartIndex={container_start}&Limit={container_size}")
            total_size = data["TotalRecordCount"]
            results.extend(EmbyItem(x) for x in data["Items"])
            container_start += container_size
            logger.ghost(f"Loaded: {total_size if container_start > total_size else container_start}/{total_size}")


        return results

    def get_collection(self, label=None):
        collections = self.EmbyServer.get(f"/Users/{self.EmbyServer.user_id}/Items?includedItemTypes=BoxSet&ParentId={self.Emby['Id']}")
        return collections["Items"]


    def __init__(self, config, params):
        super().__init__(config, params)
        self.emby = params["emby"]
        self.url = self.emby["url"]
        self.token = self.emby["token"]
        self.user_id = self.emby["user_id"]
        self.timeout = 10
        self.clean_bundles = False
        self.empty_trash = False
        self.optimize = False
        self._all_items = []

        logger.secret(self.url)
        logger.secret(self.token)
        library_name = []
        try:
            self.EmbyServer = EmbyServer(self.url, self.token, self.user_id)
            logger.info(
                f"Connected to server {self.EmbyServer.info.server_name} running version {self.EmbyServer.info.version}")
            self.Emby = None
            for s in self.EmbyServer.library:
                library_name.append(s["Name"])
                if s["Name"] == self.name:
                    self.Emby = s
                    break

            if not self.Emby:
                raise Failed(f"Emby Error: Emby Library '{params['name']} not found. Options: {library_name}")
            if self.Emby["CollectionType"] not in library_types:
                raise Failed(f"Emby Error: Emby Library must be a Movies, TV Shows, or Music library")

            self.type = self.Emby["CollectionType"]
            self._users = []
            self._all_items = []
            self._account = None
            self.is_movie = self.type == "movies"
            self.is_show = self.type == "tvshows"
            self.is_music = self.type == "music"
            self.is_other = False
            logger.info(f"Connected to library {params['name']}")
            logger.info(f"Type: {self.type}")



        except Exception as e:
            logger.error(f"Could not connect to Emby server: {e}")
            raise e

    def cache_items(self):
        logger.info("")
        logger.separator(f"Caching {self.name} Library Items", space=False, border=False)
        logger.info("")
        items = self.get_all()
        for item in items:
            self.cached_items[item.ratingKey] = item
        return items

    def get_server(self):
        return self.EmbyServer

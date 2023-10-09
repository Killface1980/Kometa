import os
from typing import Any

from modules.library import Library
from functools import cached_property
from modules import builder, util
import requests

from modules.util import Failed

logger = util.logger

library_types = ["movies", "Music", "TV Shows"]
builders = ["emby_all", "emby_collectionless", "emby_search"]

library_get_items_type = {
    "movies": "Movie",
    "tvshows": "Series",
}

method_alias = {
    "actors": "actor", "role": "actor", "roles": "actor",
    "show_actor": "actor", "show_actors": "actor", "show_role": "actor", "show_roles": "actor",
    "collections": "collection", "plex_collection": "collection",
    "show_collections": "collection", "show_collection": "collection",
    "content_ratings": "content_rating", "contentRating": "content_rating", "contentRatings": "content_rating",
    "countries": "country",
    "decades": "decade",
    "directors": "director",
    "genres": "genre",
    "labels": "label",
    "collection_minimum": "minimum_items",
    "playlist_minimum": "minimum_items",
    "save_missing": "save_report",
    "rating": "critic_rating",
    "show_user_rating": "user_rating",
    "video_resolution": "resolution",
    "tmdb_trending": "tmdb_trending_daily",
    "play": "plays", "show_plays": "plays", "show_play": "plays", "episode_play": "episode_plays",
    "originally_available": "release", "episode_originally_available": "episode_air_date",
    "episode_release": "episode_air_date", "episode_released": "episode_air_date",
    "show_originally_available": "release", "show_release": "release", "show_air_date": "release",
    "released": "release", "show_released": "release", "max_age": "release",
    "studios": "studio",
    "networks": "network",
    "producers": "producer",
    "writers": "writer",
    "years": "year", "show_year": "year", "show_years": "year",
    "show_title": "title", "filter": "filters",
    "seasonyear": "year", "isadult": "adult", "startdate": "start", "enddate": "end", "averagescore": "score",
    "minimum_tag_percentage": "min_tag_percent", "minimumtagrank": "min_tag_percent",
    "minimum_tag_rank": "min_tag_percent",
    "anilist_tag": "anilist_search", "anilist_genre": "anilist_search", "anilist_season": "anilist_search",
    "mal_producer": "mal_studio", "mal_licensor": "mal_studio",
    "trakt_recommended": "trakt_recommended_weekly", "trakt_watched": "trakt_watched_weekly",
    "trakt_collected": "trakt_collected_weekly",
    "collection_changes_webhooks": "changes_webhooks",
    "radarr_add": "radarr_add_missing", "sonarr_add": "sonarr_add_missing",
    "trakt_recommended_personal": "trakt_recommendations",
    "collection_level": "builder_level", "overlay_level": "builder_level",
}

modifier_alias = {".greater": ".gt", ".less": ".lt"}


class SystemInfo:

    def __init__(self, json):
        self.version = json["Version"]
        self.server_name = json["ServerName"]


class Label:

    def __init__(self):
        self.tag = "PMM"


class Collection:
    def __init__(self, json):
        self.title = json["Name"]
        self.labels = [Label()]


class Guid:

    def __init__(self, type, id):
        self.id = f"{type}://{id}"


class EmbyItem:

    def __init__(self, json, type):
        self.ratingKey = json["Id"]
        self.title = json["Name"]
        self.guid = f"emby://{type}/{self.ratingKey}"
        self.guids = []
        if "ProviderIds" in json:
            if "Imdb" in json["ProviderIds"]:
                self.guids.append(Guid("imdb", json['ProviderIds']['Imdb']))
            if "Tmdb" in json["ProviderIds"]:
                self.guids.append(Guid("tmdb", json['ProviderIds']['Tmdb']))
            if "Tvdb" in json["ProviderIds"]:
                self.guids.append(Guid("tvdb", json['ProviderIds']['Tvdb']))


class EmbyServer:

    def __init__(self, url, token, user_id):
        self.url = url
        self.token = token
        self.user_id = user_id
        self.machineIdentifier = ""
        self.friendlyName = ""
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

    def fetchItems(self, uri_args):
        pass

    def split(self, text):
        attribute, modifier = os.path.splitext(str(text).lower())
        attribute = method_alias[attribute] if attribute in method_alias else attribute
        modifier = modifier_alias[modifier] if modifier in modifier_alias else modifier

        if attribute == "add_to_arr":
            attribute = "radarr_add_missing" if self.is_movie else "sonarr_add_missing"
        elif attribute in ["arr_tag", "arr_folder"]:
            attribute = f"{'rad' if self.is_movie else 'son'}{attribute}"
        elif attribute in builder.date_attributes and modifier in [".gt", ".gte"]:
            modifier = ".after"
        elif attribute in builder.date_attributes and modifier in [".lt", ".lte"]:
            modifier = ".before"
        final = f"{attribute}{modifier}"
        if text != final:
            logger.warning(f"Collection Warning: {text} attribute will run as {final}")
        return attribute, modifier, final

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
        try:
            return item.labels
        except Exception as e:
            raise Failed(f"Item: {item.title} Labels failed to load")

    def get_language(self):
        return self.language

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
                f"/Users/{self.EmbyServer.user_id}/Items?includedItemTypes={library_get_items_type[self.type]}&ParentId={self.Emby['Id']}&Fields=ProviderIds&StartIndex={container_start}&Limit={container_size}")
            total_size = data["TotalRecordCount"]
            results.extend(EmbyItem(x, self.type) for x in data["Items"])
            container_start += container_size
            logger.ghost(f"Loaded: {total_size if container_start > total_size else container_start}/{total_size}")

        return results

    def get_all_collections(self, label=None):
        collections = self.EmbyServer.get(
            f"/Users/{self.EmbyServer.user_id}/Items?IncludeItemTypes=BoxSet&ParentId={self.Emby['Id']}&Recursive=true")
        return [Collection(x) for x in collections["Items"]]

    def get_collection(self, data, force_search=False, debug=True):
        if isinstance(data, Collection):
            return data
        elif isinstance(data, int) and not force_search:
            return self.EmbyServer.get(
                f"/Users/{self.EmbyServer.user_id}/Items/{data}&IncludeItemTypes=BoxSet&ParentId={self.Emby['Id']}")
        else:
            cols = self.get_all_collections()
            for col in cols:
                if col.title == data:
                    return col
            if debug:
                logger.debug("")
                for d in cols:
                    logger.debug(f"Found Collection: {d.title}")
                logger.debug(f"Looking for: {data}")
        raise Failed(f"Emby Error: Collection not found: {data}")

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
        self.language = "en"

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



    def get_server(self):
        return self.EmbyServer

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from geojson_pydantic.geometries import (
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
    _GeometryBase,
)
from pydantic import BaseModel, Field, validator
from pydantic.datetime_parse import parse_datetime

from stac_pydantic.api.extensions.fields import FieldsExtension
from stac_pydantic.api.extensions.query import Operator
from stac_pydantic.api.extensions.sort import SortExtension
from stac_pydantic.shared import BBox


class Search(BaseModel):
    """
    https://github.com/radiantearth/stac-api-spec/blob/master/api-spec.md#filter-parameters-and-fields
    """

    collections: List[str]
    ids: Optional[List[str]]
    bbox: Optional[BBox]
    intersects: Optional[
        Union[Point, MultiPoint, LineString, MultiLineString, Polygon, MultiPolygon]
    ]
    datetime: Optional[str]
    limit: int = 10
    field: Optional[FieldsExtension] = Field(None, alias="fields")
    query: Optional[Dict[str, Dict[Operator, Any]]]
    sortby: Optional[List[SortExtension]]

    @property
    def start_date(self) -> Optional[datetime]:
        values = self.datetime.split("/")
        if len(values) == 1:
            return None
        if values[0] == "..":
            return None
        return parse_datetime(values[0])

    @property
    def end_date(self) -> Optional[datetime]:
        values = self.datetime.split("/")
        if len(values) == 1:
            return parse_datetime(values[0])
        if values[1] == "..":
            return None
        return parse_datetime(values[1])

    @validator("intersects")
    def validate_spatial(cls, v, values):
        if v and values["bbox"]:
            raise ValueError("intersects and bbox parameters are mutually exclusive")
        return v

    @validator("datetime")
    def validate_datetime(cls, v):
        if "/" in v:
            values = v.split("/")
        else:
            # Single date is interpreted as end date
            values = ["..", v]

        dates = []
        for value in values:
            if value == "..":
                dates.append(value)
                continue

            parse_datetime(value)
            dates.append(value)

        if ".." not in dates:
            if parse_datetime(dates[0]) > parse_datetime(dates[1]):
                raise ValueError(
                    "Invalid datetime range, must match format (begin_date, end_date)"
                )

        return v

    @property
    def spatial_filter(self) -> Optional[_GeometryBase]:
        """Return a geojson-pydantic object representing the spatial filter for the search request.

        Check for both because the ``bbox`` and ``intersects`` parameters are mutually exclusive.
        """
        if self.bbox:
            return Polygon(
                coordinates=[
                    [
                        [self.bbox[0], self.bbox[3]],
                        [self.bbox[2], self.bbox[3]],
                        [self.bbox[2], self.bbox[1]],
                        [self.bbox[0], self.bbox[1]],
                        [self.bbox[0], self.bbox[3]],
                    ]
                ]
            )
        if self.intersects:
            return self.intersects
        return

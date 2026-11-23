package com.ssafy.a204.EodiLog.feed;

import static io.swagger.v3.oas.annotations.media.Schema.RequiredMode.REQUIRED;
import com.ssafy.a204.EodiLog.feed.FeedDtos.FeedCard;
import com.ssafy.a204.EodiLog.place.dto.PlaceView;
import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description="Discovery recommendation: a feed or a place, built only from published feeds the requester is allowed to see")
public record DiscoveryItem(
        @Schema(description="Item kind", example="FEED", allowableValues={"FEED","PLACE"}, requiredMode=REQUIRED) Type type,
        @Schema(description="Feed card when type is FEED, otherwise null", requiredMode=REQUIRED, nullable=true) FeedCard feed,
        @Schema(description="Place when type is PLACE, otherwise null", requiredMode=REQUIRED, nullable=true) PlaceView place,
        @Schema(description="Short Korean reason computed only from allowed feeds", example="좋아요 12개", requiredMode=REQUIRED) String reason) {
    public enum Type { FEED, PLACE }
}

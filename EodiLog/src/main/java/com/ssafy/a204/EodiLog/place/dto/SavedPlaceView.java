package com.ssafy.a204.EodiLog.place.dto;

import java.util.List;
import java.util.UUID;

public record SavedPlaceView(PlaceView place, List<SavedBy> savedBy, long savedCount) {
    public record SavedBy(UUID memberId, String memo) {}
}

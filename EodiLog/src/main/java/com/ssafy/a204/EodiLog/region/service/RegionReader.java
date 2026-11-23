package com.ssafy.a204.EodiLog.region.service;

import java.util.*;
import com.ssafy.a204.EodiLog.region.dto.RegionView;

public interface RegionReader {
    Optional<RegionView> find(UUID regionId);
    Map<UUID, RegionView> findAll(Collection<UUID> regionIds);
}

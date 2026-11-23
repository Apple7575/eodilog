package com.ssafy.a204.EodiLog.region.repository;

import com.ssafy.a204.EodiLog.region.domain.Region;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RegionRepository extends JpaRepository<Region, UUID> {
}

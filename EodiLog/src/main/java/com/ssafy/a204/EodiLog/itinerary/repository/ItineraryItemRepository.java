package com.ssafy.a204.EodiLog.itinerary.repository;

import com.ssafy.a204.EodiLog.itinerary.domain.ItineraryItem;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ItineraryItemRepository extends JpaRepository<ItineraryItem, UUID> {

	List<ItineraryItem> findAllByItineraryIdOrderByDayAscSequenceAsc(UUID itineraryId);

}

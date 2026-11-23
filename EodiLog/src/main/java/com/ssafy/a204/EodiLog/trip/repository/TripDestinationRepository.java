package com.ssafy.a204.EodiLog.trip.repository;

import com.ssafy.a204.EodiLog.trip.domain.TripDestination;
import com.ssafy.a204.EodiLog.trip.domain.TripDestinationId;
import java.util.Collection;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TripDestinationRepository extends JpaRepository<TripDestination, TripDestinationId> {

	List<TripDestination> findAllByTripIdOrderByDisplayOrder(UUID tripId);

	List<TripDestination> findAllByTripIdInOrderByDisplayOrder(Collection<UUID> tripIds);

}

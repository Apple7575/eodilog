package com.ssafy.a204.EodiLog.poll.repository;

import com.ssafy.a204.EodiLog.poll.domain.PollResult;
import java.util.Collection;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PollResultRepository extends JpaRepository<PollResult, UUID> {

	List<PollResult> findAllByCandidateIdIn(Collection<UUID> candidateIds);

}

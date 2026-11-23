package com.ssafy.a204.EodiLog.chat.repository;

import com.ssafy.a204.EodiLog.chat.domain.ChatParticipant;
import com.ssafy.a204.EodiLog.chat.domain.ChatParticipantId;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatParticipantRepository extends JpaRepository<ChatParticipant, ChatParticipantId> {

	List<ChatParticipant> findAllByRoomId(UUID roomId);

}

package com.ssafy.a204.EodiLog.expense.repository;

import com.ssafy.a204.EodiLog.expense.domain.SettlementMember;
import com.ssafy.a204.EodiLog.expense.domain.SettlementMemberId;
import java.util.Collection;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SettlementMemberRepository extends JpaRepository<SettlementMember, SettlementMemberId> {

	List<SettlementMember> findAllBySettlementIdIn(Collection<UUID> settlementIds);

}

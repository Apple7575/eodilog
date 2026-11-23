package com.ssafy.a204.EodiLog.expense.repository;

import com.ssafy.a204.EodiLog.expense.domain.SettlementTransfer;
import java.util.Collection;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SettlementTransferRepository extends JpaRepository<SettlementTransfer, UUID> {

	List<SettlementTransfer> findAllBySettlementIdIn(Collection<UUID> settlementIds);

}

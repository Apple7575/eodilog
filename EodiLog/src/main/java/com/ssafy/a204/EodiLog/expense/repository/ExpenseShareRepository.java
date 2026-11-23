package com.ssafy.a204.EodiLog.expense.repository;

import com.ssafy.a204.EodiLog.expense.domain.ExpenseShare;
import com.ssafy.a204.EodiLog.expense.domain.ExpenseShareId;
import java.util.Collection;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExpenseShareRepository extends JpaRepository<ExpenseShare, ExpenseShareId> {

	List<ExpenseShare> findAllByExpenseId(UUID expenseId);

	List<ExpenseShare> findAllByExpenseIdIn(Collection<UUID> expenseIds);

}

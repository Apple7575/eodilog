package com.ssafy.a204.EodiLog.job;
public enum JobStatus {
    QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED;
    public boolean terminalFailure() { return this == FAILED || this == CANCELLED; }
}

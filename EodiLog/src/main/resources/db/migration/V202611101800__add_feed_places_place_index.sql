-- 장소별 공개 평가·방문 요약(S15P31A204-261). 장소에서 게시 스냅샷 피드를 찾는다
CREATE INDEX idx_feed_places_place ON feed_places(place_id,feed_id);

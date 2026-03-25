-- mdiacc.drawing_requests definition

CREATE TABLE `drawing_requests` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `drawing_id` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `revision` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `auto_id` int(11) NOT NULL,
  `requested_by` int(11) NOT NULL,
  `requested_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT 'open',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=93 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- mdiacc.drawing_request_history definition

-- mdiacc.drawing_request_history definition

CREATE TABLE `drawing_request_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `request_id` int(11) NOT NULL,
  `event_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `performed_by` int(11) NOT NULL,
  `performed_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `remarks` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=258 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
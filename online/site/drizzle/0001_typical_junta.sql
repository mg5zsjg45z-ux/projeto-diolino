CREATE TABLE `media_files` (
	`id` text PRIMARY KEY NOT NULL,
	`owner` text NOT NULL,
	`object_key` text NOT NULL,
	`upload_id` text,
	`name` text NOT NULL,
	`mime` text NOT NULL,
	`size` integer NOT NULL,
	`category` text NOT NULL,
	`fingerprint` text NOT NULL,
	`status` text NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `media_owner_status` ON `media_files` (`owner`,`status`);--> statement-breakpoint
CREATE TABLE `media_parts` (
	`file_id` text NOT NULL,
	`part_number` integer NOT NULL,
	`etag` text NOT NULL,
	`size` integer NOT NULL,
	PRIMARY KEY(`file_id`, `part_number`),
	FOREIGN KEY (`file_id`) REFERENCES `media_files`(`id`) ON UPDATE no action ON DELETE no action
);

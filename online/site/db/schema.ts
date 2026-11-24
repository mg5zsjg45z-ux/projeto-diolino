import { integer, sqliteTable, text, index, primaryKey } from 'drizzle-orm/sqlite-core';
export const accounts = sqliteTable('accounts', {
  owner: text('owner').primaryKey(),
  revision: integer('revision').notNull().default(0),
  data: text('data').notNull(),
});

export const mediaFiles = sqliteTable('media_files', {
  id: text('id').primaryKey(), owner: text('owner').notNull(),
  objectKey: text('object_key').notNull(), uploadId: text('upload_id'),
  name: text('name').notNull(), mime: text('mime').notNull(),
  size: integer('size').notNull(), category: text('category').notNull(),
  fingerprint: text('fingerprint').notNull(), status: text('status').notNull(),
  createdAt: text('created_at').notNull(), updatedAt: text('updated_at').notNull(),
}, table => [index('media_owner_status').on(table.owner, table.status)]);

export const mediaParts = sqliteTable('media_parts', {
  fileId: text('file_id').notNull().references(()=>mediaFiles.id),
  partNumber: integer('part_number').notNull(), etag: text('etag').notNull(),
  size: integer('size').notNull(),
}, table => [primaryKey({columns:[table.fileId,table.partNumber]})]);

// Geometry of the table node — must match the CSS in styles.css exactly,
// because relationship edges compute their anchors from these numbers.
export const NODE_W = 222;   // 220 content + 2px border
export const HEAD_H = 39;    // 1px top border + 6px color strip + 32px name row
export const ROW_H = 30;

export const TYPES = [
  'INT', 'BIGINT', 'SMALLINT', 'DECIMAL', 'FLOAT', 'DOUBLE', 'BOOLEAN',
  'VARCHAR', 'CHAR', 'TEXT', 'DATE', 'TIME', 'DATETIME', 'TIMESTAMP',
  'JSON', 'UUID', 'BLOB',
];

export const COLORS = [
  '#e05d5d', '#e08b3d', '#c9a227', '#4f9e5f', '#3aa6a6',
  '#4a7fd6', '#8464d8', '#c163b9', '#7b8794',
];

export const CARDINALITIES = {
  one_to_one: { label: 'One to one', marks: ['1', '1'] },
  one_to_many: { label: 'One to many', marks: ['1', 'n'] },
  many_to_one: { label: 'Many to one', marks: ['n', '1'] },
};

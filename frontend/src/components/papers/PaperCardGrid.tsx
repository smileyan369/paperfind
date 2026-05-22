import type { Paper } from '../../types/paper';
import PaperCard from './PaperCard';

interface Props {
  papers: Paper[];
  isRead: (id: number) => boolean;
  onToggleStar: (id: number, starred: boolean) => void;
  onViewDetail: (id: number) => void;
  onSummarize: (id: number) => void;
  onKeywordFilter?: (keywordId: number) => void;
  summarizingId: number | null;
  highlightIds?: Set<number>;
  aiAvailable?: boolean;
}

export default function PaperCardGrid({ papers, isRead, onToggleStar, onViewDetail, onSummarize, onKeywordFilter, summarizingId, highlightIds, aiAvailable = true }: Props) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {papers.map(p => (
        <PaperCard
          key={p.id}
          paper={p}
          isRead={isRead(p.id)}
          onToggleStar={onToggleStar}
          onViewDetail={onViewDetail}
          onSummarize={onSummarize}
          onKeywordFilter={onKeywordFilter}
          summarizing={summarizingId === p.id}
          highlight={highlightIds?.has(p.id) ?? false}
          aiAvailable={aiAvailable}
        />
      ))}
    </div>
  );
}

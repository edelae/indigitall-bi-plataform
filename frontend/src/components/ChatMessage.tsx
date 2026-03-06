import { Bot, User } from 'lucide-react'

interface Props {
  role: 'user' | 'assistant'
  content: string
  children?: React.ReactNode // For inline results
}

export default function ChatMessage({ role, content, children }: Props) {
  if (role === 'user') {
    return (
      <div className="flex justify-end mb-4 animate-fade-in">
        <div className="max-w-[70%] flex items-start gap-2">
          <div className="bg-primary text-white px-4 py-2.5 rounded-2xl rounded-tr-sm text-sm leading-relaxed">
            {content}
          </div>
          <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0">
            <User size={14} className="text-primary" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start mb-4 animate-fade-in">
      <div className="max-w-[85%] flex items-start gap-2">
        <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center flex-shrink-0">
          <Bot size={14} className="text-white" />
        </div>
        <div>
          <div className="bg-surface px-4 py-2.5 rounded-2xl rounded-tl-sm text-sm leading-relaxed text-text-dark">
            {content}
          </div>
          {children && (
            <div className="mt-3">
              {children}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

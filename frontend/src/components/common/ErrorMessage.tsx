export default function ErrorMessage({ message = '加载失败，请重试' }: { message?: string }) {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="text-center">
        <div className="text-red-500 text-lg mb-2">出错了</div>
        <p className="text-gray-500">{message}</p>
      </div>
    </div>
  );
}

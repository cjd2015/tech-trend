export default function StatusBanner({ message }) {
  if (!message) return null
  return (
    <div className="status-banner">
      {message}
    </div>
  )
}

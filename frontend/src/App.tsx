import { BrowserRouter } from 'react-router-dom'
import { SessionProvider } from './context/SessionContext'
import { AppRouter } from './router'

function App() {
  return (
    <BrowserRouter>
      <SessionProvider>
        <AppRouter />
      </SessionProvider>
    </BrowserRouter>
  )
}

export default App

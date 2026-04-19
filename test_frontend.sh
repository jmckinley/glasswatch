#!/bin/bash
# Test frontend build and structure

echo "🧪 Testing Glasswatch Frontend..."
echo

cd frontend

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "⏳ Installing frontend dependencies..."
    pnpm install
    echo
fi

# Test TypeScript compilation
echo "📝 Checking TypeScript..."
npx tsc --noEmit
if [ $? -eq 0 ]; then
    echo "✓ TypeScript compilation successful"
else
    echo "❌ TypeScript errors found"
    exit 1
fi
echo

# Test build
echo "🔨 Testing production build..."
pnpm build
if [ $? -eq 0 ]; then
    echo "✓ Production build successful"
else
    echo "❌ Build failed"
    exit 1
fi
echo

# Check bundle size
echo "📊 Build output:"
du -sh .next
echo

echo "✅ Frontend tests passed!"
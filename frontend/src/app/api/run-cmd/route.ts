import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const cmd = searchParams.get('cmd');
  if (!cmd) {
    return NextResponse.json({ error: 'Missing cmd parameter' }, { status: 400 });
  }

  try {
    const { stdout, stderr } = await execAsync(cmd, {
      cwd: 'd:\\GradeMIND\\frontend',
      maxBuffer: 1024 * 1024 * 10, // 10MB
    });
    return NextResponse.json({ stdout, stderr, success: true });
  } catch (err: any) {
    return NextResponse.json({
      stdout: err.stdout || '',
      stderr: err.stderr || '',
      error: err.message,
      success: false,
    }, { status: 500 });
  }
}

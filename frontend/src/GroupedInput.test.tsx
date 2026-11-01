import {useState} from 'react';
import {render,screen,fireEvent} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {it,expect} from 'vitest';
import GroupedInput,{formatGroupedNumber} from './GroupedInput';
function Example({mode='number'}:{mode?:'number'|'search'}){
 const [raw,setRaw]=useState('');
 return <><GroupedInput aria-label="입력" mode={mode} value={raw} onChange={e=>setRaw(e.target.value)}/><output aria-label="원본">{raw}</output></>;
}
it('groups integer digits without changing precision, zeroes or decimals',()=>{
 expect(formatGroupedNumber('3000000')).toBe('3,000,000');
 expect(formatGroupedNumber('300000000')).toBe('300,000,000');
 expect(formatGroupedNumber('12345678901234567890')).toBe('12,345,678,901,234,567,890');
 expect(formatGroupedNumber('3.25')).toBe('3.25');expect(formatGroupedNumber('0')).toBe('0');
 expect(formatGroupedNumber('1e3')).toBe('1e3');expect(formatGroupedNumber('')).toBe('');
});
it('types, pastes and clears formatted money while emitting raw values',async()=>{
 const user=userEvent.setup();render(<Example/>);const input=screen.getByLabelText('입력');
 await user.type(input,'3000000');expect(input).toHaveValue('3,000,000');expect(screen.getByLabelText('원본')).toHaveTextContent(/^3000000$/);
 await user.clear(input);await user.paste('300,000,000');expect(input).toHaveValue('300,000,000');expect(screen.getByLabelText('원본')).toHaveTextContent(/^300000000$/);
 await user.clear(input);expect(input).toHaveValue('');expect(screen.getByLabelText('원본')).toBeEmptyDOMElement();
});
it('can backspace and delete across grouping separators without getting stuck',async()=>{
 const user=userEvent.setup();render(<Example/>);const input=screen.getByLabelText('입력') as HTMLInputElement;
 await user.type(input,'1234');input.setSelectionRange(2,2);await user.keyboard('{Backspace}');expect(input).toHaveValue('234');
 await user.clear(input);await user.type(input,'1234');input.setSelectionRange(1,1);await user.keyboard('{Delete}');expect(input).toHaveValue('134');
});
it('keeps a middle edit at its logical position',async()=>{
 const user=userEvent.setup();render(<Example/>);const input=screen.getByLabelText('입력') as HTMLInputElement;
 await user.type(input,'1234567');input.setSelectionRange(4,4);await user.keyboard('9');expect(input).toHaveValue('12,394,567');expect(input.selectionStart).toBe(5);
});
it('groups numeric-only searches but preserves Korean, spaces and year text',async()=>{
 const user=userEvent.setup();render(<Example mode="search"/>);const input=screen.getByLabelText('입력');
 await user.type(input,'3000000');expect(input).toHaveValue('3,000,000');expect(screen.getByLabelText('원본')).toHaveTextContent(/^3000000$/);
 fireEvent.change(input,{target:{value:'2026 청년, 월세'}});expect(input).toHaveValue('2026 청년, 월세');
});
it('retains invalid decimal or scientific inputs for existing validation rather than silently turning them into integers',()=>{
 render(<Example/>);const input=screen.getByLabelText('입력');
 fireEvent.change(input,{target:{value:'1.5'}});expect(screen.getByLabelText('원본')).toHaveTextContent(/^1.5$/);
 fireEvent.change(input,{target:{value:'1e3'}});expect(screen.getByLabelText('원본')).toHaveTextContent(/^1e3$/);
});

